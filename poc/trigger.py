from pynput import keyboard

def on_activate():
    print("✅ Hotkey triggered!")

with keyboard.GlobalHotKeys({
    '<cmd>+<shift>+j': on_activate
}) as h:
    print("🚀 Listening... Press Cmd+Shift+J")
    h.join()