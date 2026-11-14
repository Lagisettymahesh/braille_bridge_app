"""Serial link to the ESP32 Braille cell (one byte 0..63 per cell). Runs in a background thread."""
import threading, time

try:
    import serial
    from serial.tools import list_ports
except Exception:                                   # pyserial not installed: simulator only
    serial = None

VIRTUAL_PORT = 'VIRTUAL'

_state = {'running': False, 'sent': 0, 'total': 0, 'current_cell': 0, 'current_index': 0, 'port': None, 'error': None, 'stop': False}
_lock = threading.Lock()

def available():
    return True

def ports():
    p_list = [{'device': VIRTUAL_PORT, 'description': 'Virtual ESP32 Braille Cell Simulator (On-screen)'}]
    if serial:
        p_list += [{'device': p.device, 'description': p.description} for p in list_ports.comports()]
    return p_list

def status():
    with _lock:
        return {k: v for k, v in _state.items() if k != 'stop'} | {'available': available(), 'serial_installed': serial is not None}

def stop():
    with _lock:
        _state['stop'] = True

def send(port, cells, delay=1.0, baud=115200):
    if not port:
        raise ValueError('No serial port selected')
    if port != VIRTUAL_PORT and serial is None:
        raise RuntimeError('pyserial is not installed (pip install pyserial)')
    cells = [int(c) & 0x3F for c in cells][:500]
    with _lock:
        if _state['running']:
            raise RuntimeError('A transfer is already running')
        _state.update(running=True, sent=0, total=len(cells), current_cell=0, current_index=0, port=port, error=None, stop=False)

    def work():
        try:
            if port == VIRTUAL_PORT:
                for idx, c in enumerate(cells):
                    with _lock:
                        if _state['stop']:
                            break
                        _state['current_cell'] = c
                        _state['current_index'] = idx
                    t_end = time.time() + max(0.2, delay)
                    while time.time() < t_end:
                        with _lock:
                            if _state['stop']:
                                break
                        time.sleep(0.05)
                    with _lock:
                        _state['sent'] += 1
            else:
                with serial.Serial(port, baud, timeout=0.1) as s:
                    time.sleep(1.5)                    # ESP32 resets when the port opens
                    for idx, c in enumerate(cells):
                        with _lock:
                            if _state['stop']:
                                break
                            _state['current_cell'] = c
                            _state['current_index'] = idx
                        s.write(bytes([c]))
                        t_end = time.time() + max(0.2, delay)
                        while time.time() < t_end:
                            with _lock:
                                if _state['stop']:
                                    break
                            # Read any incoming line like 'NEXT' from the board button
                            if s.in_waiting:
                                line = s.readline().decode('utf-8', errors='ignore').strip()
                                if line == 'NEXT':
                                    break
                            time.sleep(0.05)
                        with _lock:
                            _state['sent'] += 1
        except Exception as e:
            with _lock:
                _state['error'] = str(e)
        finally:
            with _lock:
                _state['running'] = False
    threading.Thread(target=work, daemon=True).start()

