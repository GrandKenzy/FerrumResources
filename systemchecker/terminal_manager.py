import subprocess
import threading
import queue
import time
import uuid
import os
import platform

_WIN = platform.system().lower() == "windows"

class TerminalSession:
    def __init__(self, shell_type="powershell"):
        self.id = str(uuid.uuid4())
        self.shell_type = shell_type.lower()
        
        cmd = "powershell.exe -NoExit -Command -" if self.shell_type == "powershell" else "cmd.exe"
        if not _WIN:
            cmd = "/bin/bash"

        # Create subprocess with unbuffered I/O (or close to it)
        # In Windows, we might need a pseudo-terminal for perfect interactive usage, 
        # but for a basic web terminal, this might work if we read line by line.
        # Actually, standard pipes can be tricky with interactive prompts. 
        # A simpler approach for a stateless web UI is just running commands and getting output,
        # but the user asked for a "CMD/PowerShell" that can change prompt.
        
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
            text=True,
            bufsize=1, # Line buffered
            cwd=os.path.expanduser("~")
        )
        
        self.output_queue = queue.Queue()
        self.running = True
        
        # Start reader thread
        self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self.reader_thread.start()
        
        self.last_accessed = time.time()

    def _read_output(self):
        # Read character by character to handle prompts without newlines
        while self.running and self.process.poll() is None:
            try:
                char = self.process.stdout.read(1)
                if char:
                    self.output_queue.put(char)
                else:
                    break
            except Exception:
                break
        self.running = False

    def write(self, command):
        self.last_accessed = time.time()
        if self.process.poll() is None:
            try:
                self.process.stdin.write(command + "\n")
                self.process.stdin.flush()
            except Exception as e:
                self.output_queue.put(f"\n[Error de escritura: {e}]\n")

    def read_all(self):
        self.last_accessed = time.time()
        output = ""
        while not self.output_queue.empty():
            try:
                output += self.output_queue.get_nowait()
            except queue.Empty:
                break
        return output

    def kill(self):
        self.running = False
        try:
            self.process.terminate()
        except:
            pass

# Global session manager
_sessions = {}

def create_session(shell_type="powershell"):
    # Clean up old sessions
    now = time.time()
    to_delete = [sid for sid, s in _sessions.items() if now - s.last_accessed > 3600 or not s.running]
    for sid in to_delete:
        _sessions[sid].kill()
        del _sessions[sid]

    session = TerminalSession(shell_type)
    _sessions[session.id] = session
    return session.id

def write_to_session(session_id, command):
    if session_id in _sessions:
        _sessions[session_id].write(command)
        return True
    return False

def read_from_session(session_id):
    if session_id in _sessions:
        return _sessions[session_id].read_all()
    return ""

def kill_session(session_id):
    if session_id in _sessions:
        _sessions[session_id].kill()
        del _sessions[session_id]
        return True
    return False
