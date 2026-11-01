"""Static and executable Lua API simulation; no game binary or user saves needed."""
import ctypes
import ctypes.util
from pathlib import Path
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "addons" / "AZSEControlCenter" if (ROOT / "addons" / "AZSEControlCenter").is_dir() else ROOT / "AZSEControlCenter"


class PackageTests(unittest.TestCase):
    def test_vanilla_toc_layout(self):
        toc = (ADDON / "AZSEControlCenter.toc").read_text(encoding="utf-8")
        self.assertIn("## Interface: 11200", toc)
        self.assertIn("## SavedVariables: AZSCC_DB", toc)
        self.assertIn("Core.lua", toc)
        self.assertNotIn(".dll", toc.lower())

    def test_all_menu_categories_and_documented_real_actions(self):
        lua = (ADDON / "Core.lua").read_text(encoding="utf-8")
        for tab in ("Dashboard", "Interface", "Level-ups", "Builds", "Mods", "Cheats", "Settings"):
            self.assertIn('"' + tab + '"', lua)
        for function in ("AZS_SetHudShown", "AZS_IsHudShown", "AZS_SetStoringLevels",
                         "AZS_OpenStoredLevels", "AZS_GetMeter"):
            self.assertIn(function, lua)
        for old_modern in ("string.match", "_G[", "loadstring(", "RunScript("):
            self.assertNotIn(old_modern, lua)
        self.assertIn("NOT CONNECTED", lua)
        self.assertIn('SLASH_AZSCC1 = "/azcc"', lua)
        self.assertIn('SLASH_AZSCC2 = "/azmenu"', lua)

    def test_zip_contains_correct_root_folder(self):
        archive = ROOT.parent / 'AZSE-InGame-Control-Center-0.1.0-preview.zip'
        if archive.is_file():
            with zipfile.ZipFile(archive) as f:
                self.assertEqual(sorted(f.namelist()),
                                 ['AZSEControlCenter/AZSEControlCenter.toc', 'AZSEControlCenter/Core.lua'])


class RuntimeMockTests(unittest.TestCase):
    def test_lua_syntax_and_mocked_in_game_controls(self):
        lib = ctypes.util.find_library("lua5.4") or ctypes.util.find_library("lua5.3")
        if not lib:
            self.skipTest("No system Lua runtime; static package tests still run")
        L = ctypes.CDLL(lib)
        L.luaL_newstate.restype = ctypes.c_void_p
        L.luaL_openlibs.argtypes = [ctypes.c_void_p]
        L.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        L.luaL_loadstring.restype = ctypes.c_int
        L.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ssize_t, ctypes.c_void_p]
        L.lua_pcallk.restype = ctypes.c_int
        L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        L.lua_tolstring.restype = ctypes.c_char_p
        L.lua_close.argtypes = [ctypes.c_void_p]
        state = L.luaL_newstate()
        self.assertTrue(state)
        try:
            L.luaL_openlibs(state)
            shim = '''
            table.getn = function(t) return #t end
            math.mod = function(a,b) return a%b end
            frames = {}
            local function object(name)
              local o = {scripts={},visible=true,name=name}
              function o:SetWidth(v) self.width=v end
              function o:SetHeight(v) self.height=v end
              function o:SetPoint(...) end
              function o:SetFrameStrata(...) end
              function o:SetScale(v) self.scale=v end
              function o:SetMovable(...) end
              function o:EnableMouse(...) end
              function o:RegisterForDrag(...) end
              function o:RegisterEvent(...) end
              function o:SetScript(name,callback) self.scripts[name]=callback end
              function o:CreateTexture(...) return object('texture') end
              function o:CreateFontString(...) return object('font') end
              function o:SetTexture(...) end
              function o:SetAllPoints(...) end
              function o:SetText(value) self.text=value end
              function o:SetJustifyH(...) end
              function o:SetJustifyV(...) end
              function o:Hide() self.visible=false end
              function o:Show() self.visible=true end
              function o:IsShown() return self.visible end
              function o:StartMoving() end
              function o:StopMovingOrSizing() end
              return o
            end
            UIParent=object('parent')
            function CreateFrame(kind,name,parent,template)
              local f=object(name)
              if name then frames[name]=f end
              if not name then lastAnonFrame=f end
              return f
            end
            DEFAULT_CHAT_FRAME={AddMessage=function(self,msg) end}
            SlashCmdList={}
            AZS_RUN={k=42,lvl=11}
            function AZS_GetPhase() return 'playing' end
            function AZS_GetRunTime() return 65 end
            function AZS_GetMeter() return {{name='Test Bolt'}}, 999, 12 end
            hud = {}
            function AZS_SetHudShown(part,yes) hud[part]=yes end
            function AZS_IsHudShown(part) return hud[part] ~= false end
            store = false
            function AZS_IsStoringLevels() return store end
            function AZS_SetStoringLevels(value) store=value end
            function AZS_GetStoredLevels() return 3 end
            opened=0
            function AZS_OpenStoredLevels() opened=opened+1 end
            addons={'AZSEControlCenter','OtherHUD'}
            mods={true,true}
            function GetNumAddOns() return #addons end
            function GetAddOnInfo(index) return addons[index],addons[index] end
            function GetAddOnEnableState(who,index) return mods[index] and 2 or 0 end
            function EnableAddOn(index) mods[index]=true end
            function DisableAddOn(index) mods[index]=false end
            function SaveAddOns() end
            '''
            source = (ADDON / "Core.lua").read_text(encoding="utf-8")
            checks = '''
            assert(SLASH_AZSCC1 == '/azcc')
            event='VARIABLES_LOADED'
            lastAnonFrame.scripts.OnEvent()
            SlashCmdList.AZSCC('')
            assert(frames.AZSCCPanel.visible)
            assert(frames.AZSCCLauncher.visible)
            -- Interface tab, change clock setting through genuine facade.
            frames.AZSCCTab2.scripts.OnClick()
            assert(string.find(frames.AZSCCTab2.text, 'Interface'))
            frames.AZSCCRow1.scripts.OnClick()
            assert(hud.clock == false)
            -- Level-up tab controls actual store feature.
            frames.AZSCCTab3.scripts.OnClick()
            frames.AZSCCRow1.scripts.OnClick()
            assert(store == true)
            frames.AZSCCRow2.scripts.OnClick()
            assert(opened == 1)
            -- Mod tab: disable another addon, not ourselves.
            frames.AZSCCTab5.scripts.OnClick()
            frames.AZSCCRow1.scripts.OnClick()
            assert(mods[1] == true)
            frames.AZSCCRow2.scripts.OnClick()
            assert(mods[2] == false)
            -- Cheat tab states unavailable, never mutates run.
            frames.AZSCCTab6.scripts.OnClick()
            assert(string.find(frames.AZSCCRow1.text, 'Unavailable'))
            frames.AZSCCRow1.scripts.OnClick()
            assert(AZS_RUN.k == 42)
            -- Reset stock HUD via slash.
            SlashCmdList.AZSCC('reset')
            assert(hud.clock == true)
            -- Settings persists scale.
            frames.AZSCCTab7.scripts.OnClick()
            frames.AZSCCRow2.scripts.OnClick()
            assert(type(AZSCC_DB.uiScale) == 'number')
            '''
            for chunk in (shim, source, checks):
                result = L.luaL_loadstring(state, chunk.encode('utf-8'))
                if result == 0:
                    result = L.lua_pcallk(state, 0, 0, 0, 0, None)
                if result:
                    err = L.lua_tolstring(state, -1, None)
                    self.fail('Lua mock failed: ' + (err.decode('utf-8') if err else str(result)))
        finally:
            L.lua_close(state)

if __name__ == '__main__':
    unittest.main()
