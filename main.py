import subprocess

script = '''
tell application "System Events"
    set windowList to ""
    repeat with proc in (every process whose background only is false)
        try
            repeat with w in (windows of proc)
                set windowList to windowList & name of w & linefeed
            end repeat
        end try
    end repeat
end tell
return windowList
'''
res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
print(res.stdout)
