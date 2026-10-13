"""Small stdio MCP client for the pinned Craft CLIs. Never starts an unconfined session."""
import json, os, queue, signal, subprocess, threading, time

class McpSession:
    def __init__(self, cli, root, write_root, deadline):
        self.deadline, self.request_id = deadline, 0
        self.responses, self.errors = queue.Queue(), []
        self.proc = subprocess.Popen([str(cli), 'mcp', '--automation-read-root', str(root),
            '--automation-write-root', str(write_root)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, start_new_session=True)
        def read_stdout():
            for line in self.proc.stdout:
                self.responses.put(line)
            self.responses.put(None)
        def read_stderr():
            for line in self.proc.stderr:
                self.errors.append(line.rstrip())
                self.errors[:] = self.errors[-40:]
        threading.Thread(target=read_stdout, daemon=True).start()
        threading.Thread(target=read_stderr, daemon=True).start()
        try:
            self.request('initialize', {'protocolVersion':'2024-11-05','capabilities':{},
                'clientInfo':{'name':'patio-artcraft','version':'0.2'}})
            self._send({'jsonrpc':'2.0','method':'notifications/initialized'})
        except BaseException:
            self.close()
            raise
    def _send(self, value):
        self.proc.stdin.write(json.dumps(value)+'\n'); self.proc.stdin.flush()
    def request(self, method, params):
        self.request_id += 1
        self._send({'jsonrpc':'2.0','id':self.request_id,'method':method,'params':params})
        while True:
            left = self.deadline - time.monotonic()
            if left <= 0: raise TimeoutError('MCP node time budget exhausted')
            try: line = self.responses.get(timeout=left)
            except queue.Empty: raise TimeoutError('MCP node time budget exhausted')
            if line is None: raise RuntimeError('MCP stopped: '+'; '.join(self.errors))
            response = json.loads(line)
            if response.get('id') != self.request_id: continue
            if 'error' in response: raise RuntimeError(json.dumps(response['error']))
            return response['result']
    def tool(self, name, args):
        result = self.request('tools/call', {'name':name,'arguments':args})
        text = '\n'.join(c['text'] for c in result.get('content',[]) if c.get('type') == 'text')
        if result.get('isError'): raise RuntimeError(text)
        if 'structuredContent' in result: return result['structuredContent']
        try: return json.loads(text)
        except json.JSONDecodeError: return {'text':text}
    def close(self):
        if self.proc.poll() is None:
            os.killpg(self.proc.pid, signal.SIGTERM)
            try: self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(self.proc.pid, signal.SIGKILL); self.proc.wait(timeout=2)
        for stream in (self.proc.stdin,self.proc.stdout,self.proc.stderr):
            stream.close()
    def __enter__(self): return self
    def __exit__(self, *args): self.close()
