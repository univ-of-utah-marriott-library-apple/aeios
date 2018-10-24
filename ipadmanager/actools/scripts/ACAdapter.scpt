#!/usr/bin/osascript

-- AppleScriptObjC FUNCTIONS

use framework "Foundation"

on convertASToJSON(ascptData)
	-- convert AppleScript Data to JSON
	-- adapted from [ShaneStanley](https://forum.latenightsw.com/t/applescript-record-to-json/668) 
	-- Thank you Shane!
	local nsData, nsError, json
	set {nsData, nsError} to current application's NSJSONSerialization's dataWithJSONObject:ascptData options:0 |error|:(reference)
	if nsData is missing value then error (theError's localizedDescription() as text) number -10000
	set json to current application's NSString's alloc()'s initWithData:nsData encoding:(current application's NSUTF8StringEncoding)
	return json as text
end convertASToJSON

on convertJSONToAS(jsonStr)
	-- convert JSON string to AppleScript Data
	-- adapted from [ShaneStanley](https://forum.latenightsw.com/t/applescript-record-to-json/668) 
	-- Thank you Shane!
	local nsStr, nsResult, nsData, nsError
	set nsStr to current application's NSString's stringWithString:jsonStr
	set nsData to nsStr's dataUsingEncoding:(current application's NSUTF8StringEncoding)
	-- convert to Cocoa object
	set {nsResult, nsError} to current application's NSJSONSerialization's JSONObjectWithData:nsData options:0 |error|:(reference)
	if nsResult is missing value then error (nsError's localizedDescription() as text) number -10000
	return item 1 of ((current application's NSArray's arrayWithObject:nsResult) as list)
end convertJSONToAS

on buildRecord(keys, values)
	-- if this is inside a "System Events" tell, things get really weird
	local nsDict
	set nsDict to (current application's NSDictionary's dictionaryWithObjects:values forKeys:keys)
	return item 1 of ((current application's NSArray's arrayWithObject:nsDict) as list)
end buildRecord

on getRecordValue(kStr, ASRecord)
	-- adapted from (https://forum.keyboardmaestro.com/t/making-applescript-records-dynamic-using-asobjc/4082)
	local nsDict, nsResult, tmp
	set nsDict to current application's NSDictionary's dictionaryWithDictionary:ASRecord
	set nsResult to nsDict's objectForKey:kStr
	set tmp to current application's NSArray's arrayWithArray:{nsResult}
	return item 1 of (tmp as list)
end getRecordValue

-- GUI SETUP

on launchAppleConfigurator()
	tell application "System Events"
		if "Apple Configurator 2" is not in (name of processes) then
			-- this will fail if finder can't find the application
			-- (like when Mac Apps are excluded from finder)
			tell application "Apple Configurator 2" to activate
			-- this is a stupid hacky way to make sure things don't happen too quickly
			-- because the scroll area will always exist in any window view, we're just going
			-- to wait for it to appear before continuing on with the script, BUT, we also
			-- don't want to wait forever, if something goes wrong
			set cntdwn to 10
			repeat until (first scroll area of window 1 of process "Apple Configurator 2" exists) or (cntdwn < 1)
				set cntdwn to (cntdwn - 1)
				delay 1
			end repeat
			if cntdwn is 0 then
				error "no usuable windows appeared on launch" number 9501
			end if
		end if
	end tell
end launchAppleConfigurator

on maximize(targetWindow)
	local x, y, w, h
	-- use Finder to get the size of the desktop (not sure of another way)
	tell application "Finder" to set {x, y, w, h} to the bounds of the desktop's window
	tell application "System Events" to tell process "Apple Configurator 2"
		-- can't set the bounds, but we can set the position and then the size
		set targetWindow's position to {x, y}
		set targetWindow's size to {w, h}
	end tell
end maximize

on putWindowIntoListViewMode(targetWindow)
	-- Identifying devices largely depends on information that's only available in List View
	tell application "System Events" to tell process "Apple Configurator 2"
		try
			-- if this doesn't raise an error, the window is already in List View
			set inTableView to first table of first scroll area of targetWindow
		on error errstr number errno
			-- this can probably be trapped by a specific error number
			-- log ("DEBUG: error: " & errstr & ": errno: " & errno)
			set frontmost to true
			-- Make sure AC is in list view (or our looping will break)
			set viewMenu to first menu of menu bar item "View" of menu bar 1
			click menu item "as List" of viewMenu
		end try
	end tell
end putWindowIntoListViewMode

-- WINDOWS

on allWindows()
	tell application "System Events" to tell process "Apple Configurator 2"
		set standardWindows to {}
		set alertWindows to {}
		repeat with w in windows
			if description of w is "standard window" then
				set end of standardWindows to w
			else if description of w is "alert" then
				set end of alertWindows to w
			else if role description of w is "dialog" then
				set end of alertWindows to w
			else
				-- log "DEBUG: unexpected window type found: properties: "
				-- set p to properties of w
				-- log (p)
				error "unexpected window description: " & (description of w) number 9101
			end if
		end repeat
		return {standardWindows, alertWindows}
	end tell
end allWindows

on deviceWindow()
	tell application "System Events" to tell process "Apple Configurator 2"
		repeat with w in windows
			if title of w is in {"All Devices", "Supervised", "Unsupervised", "Recovery"} then
				return w
			end if
		end repeat
	end tell
	error "unable to find device window" number 9502
end deviceWindow

-- UI HELPER FUNCTIONS

on parseUI(targetPrmpt)
	-- target should be limited to sheets, and dialog windows
	local _text, _buttons, _checkboxes, _alert
	set _text to {}
	set _buttons to {}
	set _checkboxes to {}
	set _alert to missing value
	tell application "System Events" to tell process "Apple Configurator 2"
		repeat with element in UI elements of targetPrmpt
			if element's class is button then
				set end of _buttons to element's title
			else if element's class is static text then
				set end of _text to element's value
			else if element's class is checkbox then
				set end of _checkboxes to element's title
			else if element's class is sheet then
				set _alert to element
			else if element's class is progress indicator then
				-- I wonder if there is information to be had from this element
				-- log ("skipping progress indicator: properties:")
				-- set p to properties of element
				-- log (p)
			else
				-- set _class to element's class
				-- log ("skipping element: " & _class & ": properties:")
				-- set p to properties of element
				-- log (p)
			end if
		end repeat
		return {{info:_text, options:_checkboxes, choices:_buttons}, _alert}
	end tell
end parseUI

on getDeviceInfo(deviceWndw)
	-- adapter until getDeviceInfo() has been replaced with getTableInfo()
	-- callers of this function expect {rows:{},devices:{}}
	-- NOTE:
	--      - once getDeviceInfo() has been phased out, this adapter 
	--        can be removed
	
	local _targetTable, _tableInfo
	tell application "System Events" to tell process "Apple Configurator 2"
		set _targetTable to first table of first scroll area of deviceWndw
	end tell
	set _tableInfo to getTableInfo(_targetTable)
	return {rows:rows of _tableInfo, devices:info of _tableInfo}
end getDeviceInfo

on getTableInfo(targetTable)
	-- TO-DO: need to test
	-- re-write of getDeviceInfo() to work on all tables
	-- blank columns should be skipped without hard coded index
	-- return {rows:{<row reference>, ...},
	--         info:{<info records>, ...}}
	local _allRows, _tableInfo, _columnKeys, _rowKeys, _rowValues
	tell application "System Events" to tell process "Apple Configurator 2"
		-- get a list of all column keys (including blank ones)
		set _columnKeys to {}
		repeat with b in buttons of targetTable's first group
			set end of _columnKeys to name of b
		end repeat
		-- save the count of keys for looping
		set columnCount to length of _columnKeys
		
		set _allRows to {}
		set _tableInfo to {}
		repeat with thisRow in targetTable's rows
			-- keep reference to the actual row, in case we want to select it later
			set end of _allRows to thisRow
			
			set _rowValues to {}
			set _rowKeys to {}
			repeat with i from 1 to columnCount
				if item i of _columnKeys is not missing value then
					set end of _rowKeys to item i of _columnKeys
					-- NOTE: this might work better by iterating cells instead of UI Elements
					set element to UI element i of thisRow
					set v to name of element
					if v is missing value then
						-- some UI Elements don't have a name and have a sub-text field instead
						set v to the (value of element's text field) as text
					end if
					set end of _rowValues to v
				end if
			end repeat
			-- HOOK: additional keys/values should be added here:
			
			-- add whether the row is currently selected
			set end of _rowKeys to "selected"
			set end of _rowValues to selected of thisRow
			
			-- create the record and append it to the list 
			set end of _tableInfo to my buildRecord(_rowKeys, _rowValues)
		end repeat
	end tell
	return {rows:_allRows, info:_tableInfo}
end getTableInfo

on selectDevices(k, targetValues)
	local _deviceWndw, _devices, _targetTable
	set _deviceWndw to first item of deviceWindow()
	-- REPLACE: getTableInfo()
	tell application "System Events" to tell process "Apple Configurator 2"
		set _targetTable to first table of first scroll area of _deviceWndw
	end tell
	set _devices to getTableInfo(_targetTable)
	selectFromTable(_devices, k, targetValues)
end selectDevices

on selectApps(appSheet, k, targetAppValues)
	tell application "System Events" to tell process "Apple Configurator 2"
		set _targetTable to first table of first scroll area of appSheet
	end tell
	set _vppapps to getTableInfo(_targetTable)
	
	-- this defeats the point of k being a variable (but we're going with it for now)
	set availableApps to {}
	repeat with appInfo in info of _vppapps
		set end of availableApps to |Name| of appInfo
	end repeat
	
	repeat with appname in targetAppValues
		if appname is not in availableApps then
			performAction(appSheet, {choice:"Cancel"})
			error "unable to find VPP app: " & appname number 9510
		end if
	end repeat
	
	tell application "System Events" to tell process "Apple Configurator 2"
		set editMenu to first menu of menu bar item "Edit" of menu bar 1
		click menu item "Select All" of editMenu
	end tell
	selectFromTable(_vppapps, k, targetAppValues)
end selectApps

on selectFromTable(tableRecord, k, targetValues)
	-- requires focus to be set on the table before calling this function
	tell application "System Events" to tell process "Apple Configurator 2"
		set editMenu to first menu of menu bar item "Edit" of menu bar 1

		-- select all rows
		set frontmost to true
		click menu item "Select All" of editMenu
		
		-- iterate list of device info records (by index)
		repeat with i from 1 to length of tableRecord's info
			set _info to item i of tableRecord's info
			-- get specified key of this device
			set v to my getRecordValue(k, _info)
			-- if info record does NOT match
			if v is not in targetValues then
				-- 	de-select row (by index)
				set _row to item i of tableRecord's |rows|
				-- log ("unselected: " & k & ": " & v)
				tell first item of _row
					set selected to false
				end tell
			-- else
				-- set _log_msg to k & ": " & v
				-- log ("selected: " & k & ": " & v)
			end if
		end repeat
	end tell
end selectFromTable

on findTargetPrompt()
	-- used to find actionable items in all windows
	local mainWndws, alertWndws
	-- get all open windows
	set {mainWndws, alertWndws} to allWindows()
	tell application "System Events" to tell process "Apple Configurator 2"
		-- because alert windows are reported last, they need to be checked for first
		if alertWndws is not {} then
			return first item of alertWndws
		else
			repeat with w in mainWndws
				try
					set progressSheet to first sheet of w
					set {status, alert} to my parseUI(progressSheet)
					if alert is not missing value then
						return alert
					else
						return progressSheet
					end if
				end try
			end repeat
		end if
	end tell
	-- if we have made it this far, there is nothing to interact with
	return missing value
end findTargetPrompt

-- ACTION/INFORMATION FUNCTIONS

on status()
	local mainWndws, alertWndws
	local _info, _alerts, _busy, _devices, deviceInfo, wndw
	set _info to missing value
	set _alerts to {}
	set _busy to false
	
	set {mainWndws, alertWndws} to allWindows()

	-- loop over standard windows ("All Devices", "Activity", "VPP Assignments"
	repeat with wndw in mainWndws
		tell application "System Events" to tell process "Apple Configurator 2"
			try
				-- will fail if nothing is currently happening on the window
				set progressSheet to first sheet of wndw
				set _busy to true
				set {_info, alertSheet} to my parseUI(progressSheet)
				if alertSheet is not missing value then
					set {alert, _} to my parseUI(alertSheet)
					set end of _alerts to alert
				end if
			end try
		end tell
	end repeat
	
	-- loop over alert windows (if any) 
	-- (I don't think there can be more than one alert, but I could be wrong)
	repeat with wndw in alertWndws
		set {end of _alerts, _} to my parseUI(wndw)
		set _busy to true
	end repeat
	return {activity:_info, busy:_busy, alerts:_alerts}
end status

on installVPPApps(targetWndw, apps)
	tell application "System Events" to tell process "Apple Configurator 2"
		set frontmost to true
		set actionMenu to first menu of menu bar item "Actions" of menu bar 1
		set addMenu to first menu of menu item "Add" of actionMenu
		try
			click menu item "Apps…" of addMenu
		on error errstr number errno
			if errno is not -1728 then
				error errstr number errno
			end if
			-- log ("moved a little too quickly")
			delay 1
			set frontmost to true
			click menu item "Apps…" of addMenu
		end try
		
		-- make sure we're in list view
		set appSheet to first sheet of targetWndw
		try
			-- check if sheet is already in list view
			set appTable to first table of appSheet's first scroll area
		on error errstr number errno
			if errno is not -1719 then
				error errstr number errno
			end if
			-- click "list view" radio button
			repeat with b in radio buttons of first radio group of appSheet
				if description of b is "list view" then
					click b
				end if
			end repeat
			set appTable to first table of appSheet's first scroll area
		end try
		-- wierd bug where table is not focused by default (for select all)
		set focused of appTable to true
	end tell
	selectApps(appSheet, "Name", apps)
	performAction(appSheet, {choice:"Add"})
end installVPPApps

on applyBlueprint(deviceWindow, blueprint)
	local confirmationPrompt, actionMenu, blueprintMenu
	tell application "System Events" to tell process "Apple Configurator 2"
		set frontmost to true
		set actionMenu to first menu of menu bar item "Actions" of menu bar 1
		set blueprintMenu to first menu of menu item "Apply" of actionMenu
		try
			set frontmost to true
			click menu item blueprint of blueprintMenu
		on error errstr number errno
			if errno is not -1728 then
				error errstr number errno
			end if
			-- log ("moved a little too quickly")
			delay 1
			set frontmost to true
			click menu item blueprint of blueprintMenu
		end try
		-- this alert always pops up asking if you are sure you want to apply to blueprint
		repeat until first sheet of deviceWindow exists
			delay 1
		end repeat
		set confirmationPrompt to first sheet of deviceWindow
	end tell
	performAction(confirmationPrompt, {choice:"Apply"})
end applyBlueprint

on performAction(targetPrompt, args)
	-- args should consist of {choice:"<button>", options:["checkbox1", checkbox2",...]}
	local choice, activity, checkbox
	-- look through all open windows and return first action prompt found
	
	if targetPrompt is missing value then
		error "no action prompts were found" number 9501
	end if
	
	try
		set choice to choice of args
	on error
		error "no button choice was specfied: " & args number 9502
	end try
	
	tell application "System Events" to tell process "Apple Configurator 2"
		-- at this point the target should be set to whatever is actionable
		set {activity, _} to my parseUI(targetPrompt)
		if choice is not in choices of activity then
			error "invalid choice: \"" & choice & "\"" number 9503
		end if
		-- handle optional checkboxes (not very strictly)
		-- skipped if user supplies incorrect options or no options at all
		try
			repeat with o in options of args
				set |checkbox| to checkbox o of targetPrompt
				if not (value of |checkbox| as boolean) then
					-- log ("checking: " & o)
					click |checkbox|
				else
					-- log (o & " already checked")
				end if
			end repeat
		end try
		
		-- log ("clicking: " & choice)
		click button choice of targetPrompt
	end tell
end performAction

on cancelAction(targetWindow)
	tell application "System Events" to tell process "Apple Configurator 2"
		set progressSheet to first sheet of targetWindow
	end tell
	performAction(progressSheet, {choice:"Cancel"})
end cancelAction

-- TESTS

on testSelectDevices()
	local testKey, testValues
	--set testKey to "UDID"
	--set testValues to {"D979D7C850F0EE0DB6ED2965616991EE815004CC", "A81308B7A3A3A1C19308301502A1B3290935137F", "B49145911238557A60CBD58490A84BA2E7520748"}
	--set testValues to {"A81308B7A3A3A1C19308301502A1B3290935137F"}
	
	set testKey to "ECID"
	-- set testValues to {"D979D7C850F0EE0DB6ED2965616991EE815004CC", "A81308B7A3A3A1C19308301502A1B3290935137F", "B49145911238557A60CBD58490A84BA2E7520748"}
	set testValues to {"0x11354C2429883A"}
	selectDevices(testKey, testValues)
end testSelectDevices

on testVPPApps()
	local args, wndw
	set args to {udids:{"FBE61F791F298C66EBB00A282F5B070C6CB9DC47"}, apps:{"Microsoft PowerPoint"}}
	set wndw to deviceWindow()
	putWindowIntoListViewMode(wndw)
	selectDevices("UDID", udids of args)
	return installVPPApps(wndw, apps of args)
end testVPPApps

on testApplyBlueprint()
	local args, wndw
	set args to {blueprint:"Install VPP Apps", udids:{"D979D7C850F0EE0DB6ED2965616991EE815004CC"}}
	set wndw to deviceWindow()
	putWindowIntoListViewMode(wndw)
	selectDevices("UDID", udids of args)
	applyBlueprint(wndw, blueprint of args)
end testApplyBlueprint

on testListDevices()
	local info, wndw
	set wndw to deviceWindow()
	set info to getDeviceInfo(wndw)
	return convertASToJSON(devices of info)
end testListDevices

-- MAIN

on run argv
	-- Launch AC if it isn't already running
	launchAppleConfigurator()
	try
		set command to first item of argv
	on error
		error "must specify command" number 9101
	end try
	
	if command is "--action" then
		try
			set json to second item of argv
		on error
			error "must specify action options" number 9101
		end try
		set args to convertJSONToAS(json)
		set targetPrompt to findTargetPrompt()
		performAction(targetPrompt, args)
		
	else if command is "--status" then
		set _status to status()
		return convertASToJSON(_status)
		
	else if command is "--cancel" then
		set wndw to deviceWindow()
		cancelAction(wndw)
		
	else if command is "--blueprint" then
		try
			set {_, json} to argv
		on error
			error "must specifiy blueprint and UDIDs" number 9101
		end try
		
		set args to convertJSONToAS(json)
		set wndw to deviceWindow()
		
		putWindowIntoListViewMode(wndw)
		selectDevices("UDID", udids of args)
		applyBlueprint(wndw, blueprint of args)
		
	else if command is "--vppapps" then
		-- need to come up with schema for this 
		try
			set {_, json} to argv
		on error
			error "must specifiy vpp apps and UDIDs" number 9101
		end try
		set args to convertJSONToAS(json)
		set wndw to deviceWindow()
		putWindowIntoListViewMode(wndw)
		selectDevices("UDID", udids of args)
		installVPPApps(wndw, apps of args)
		
	else if command is "--list" then
		set wndw to deviceWindow()
		putWindowIntoListViewMode(wndw)
		set info to getDeviceInfo(wndw)
		return convertASToJSON(devices of info)
		
	else
		error "unknown command: " & command number 9001
	end if
	return
end run
