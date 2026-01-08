#Requires AutoHotkey v2.0
#SingleInstance Force

; =========================
; CONFIG (edit these)
; =========================

; Option A (recommended): launch by executable path
UT_EXE := "C:\Program Files (x86)\UT61E+\UT61xP.exe"
; If you want to force desktop icon launching, set UT_EXE := ""

; Desktop icon location (only used if UT_EXE is blank)
ICON_X := -240
ICON_Y := 280

; Login coordinates
USER_X := 600
USER_Y := 580
PASS_X := 610
PASS_Y := 650
YES_X  := 540
YES_Y  := 710

; Credentials (placeholders)
USERNAME := ".\STAdmin"
PASSWORD := "m@yfield2025"

; Timing (ms)
T_AFTER_SHOW_DESKTOP := 400
T_AFTER_LAUNCH        := 2500
T_AFTER_CLICK         := 150
T_AFTER_TYPE          := 200

; =========================
; SETTINGS
; =========================
CoordMode "Mouse", "Screen"
CoordMode "Pixel", "Screen"
SetTitleMatchMode 2

; =========================
; MACRO
; =========================

; 1) Win + D (show desktop)
Send "#d"
Sleep T_AFTER_SHOW_DESKTOP

; 2) Open UT61XP
if (UT_EXE != "" && FileExist(UT_EXE)) {
    Run UT_EXE
} else {
    ; Fallback: click desktop icon
    MouseMove ICON_X, ICON_Y, 10
    Click
    Sleep 80
    Click  ; double click
}

Sleep T_AFTER_LAUNCH

; 3) Click username field and type
MouseMove USER_X, USER_Y, 10
Click
Sleep T_AFTER_CLICK
SendText USERNAME
Sleep T_AFTER_TYPE

; 4) Click password field and type
MouseMove PASS_X, PASS_Y, 10
Click
Sleep T_AFTER_CLICK
SendText PASSWORD
Sleep T_AFTER_TYPE

; 5) Click Yes button
MouseMove YES_X, YES_Y, 10
Click

ExitApp
