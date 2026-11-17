"""Serial interface and controller for the ESP32 Braille Cell hardware and virtual simulator.
Handles background cell streaming, hardware self-tests, and port management.
"""
import threading
import time
from typing import List, Dict, Any, Optional

try:
    import serial
    from serial.tools import list_ports
except Exception:
    serial = None

VIRTUAL_PORT = 'VIRTUAL'

_state = {
    'running': False,
    'sent': 0,
    'total': 0,
    'current_cell': 0,
    'current_index': 0,
    'port': None,
    'error': None,
    'stop': False,
    'mode': 'idle'
}
_lock = threading.Lock()


def available() -> bool:
    """Return True if hardware or virtual simulator is available."""
    return True


def ports() -> List[Dict[str, str]]:
    """List available serial communication ports including the virtual simulator."""
    p_list = [{
        'device': VIRTUAL_PORT,
        'description': 'Virtual ESP32 Braille Cell Simulator (Interactive On-screen)',
        'is_hardware': False
    }]
    if serial:
        for p in list_ports.comports():
            # Check for ESP32 / CH340 / CP210x / FTDI indicators
            desc = p.description or ''
            hwid = p.hwid or ''
            is_esp = any(k in (desc + hwid).lower() for k in ('cp210', 'ch340', 'ch341', 'uart', 'usb serial', 'esp32'))
            p_list.append({
                'device': p.device,
                'description': f"{p.description}{' [ESP32 detected]' if is_esp else ''}",
                'is_hardware': True
            })
    return p_list


def status() -> Dict[str, Any]:
    """Return current hardware controller status."""
    with _lock:
        st = {k: v for k, v in _state.items() if k != 'stop'}
    st.update({
        'available': available(),
        'serial_installed': serial is not None,
        'is_virtual': st.get('port') == VIRTUAL_PORT
    })
    return st


def stop():
    """Request the background streaming thread to halt."""
    with _lock:
        _state['stop'] = True


def ping(port: str, baud: int = 115200, timeout: float = 1.0) -> Dict[str, Any]:
    """Ping the selected port to verify connectivity and firmware response."""
    if not port or port == VIRTUAL_PORT:
        return {'ok': True, 'port': VIRTUAL_PORT, 'hardware': False, 'message': 'Virtual simulator ready.'}
    if not serial:
        raise RuntimeError('pyserial is not installed.')

    try:
        with serial.Serial(port, baud, timeout=timeout) as s:
            time.sleep(1.2)  # Wait for ESP32 reset
            s.reset_input_buffer()
            s.write(b'P\n')
            time.sleep(0.1)
            resp = s.readline().decode('utf-8', errors='ignore').strip()
            ok = 'BRAILLE_BRIDGE' in resp or 'OK' in resp
            return {'ok': ok, 'port': port, 'hardware': True, 'response': resp}
    except Exception as e:
        return {'ok': False, 'port': port, 'hardware': True, 'error': str(e)}


def test_hardware(port: str, delay: float = 0.4) -> Dict[str, Any]:
    """Run an automated diagnostic test sweeping dots 1 through 6."""
    if not port:
        raise ValueError('No serial port selected.')

    with _lock:
        if _state['running']:
            raise RuntimeError('A transmission or test is already in progress.')
        _state.update(
            running=True, sent=0, total=6, current_cell=0, current_index=0,
            port=port, error=None, stop=False, mode='test'
        )

    def run_test():
        try:
            if port == VIRTUAL_PORT:
                # Cycle dots 1 through 6: 1<<0 to 1<<5
                for i in range(6):
                    dot_code = 1 << i
                    with _lock:
                        if _state['stop']:
                            break
                        _state['current_cell'] = dot_code
                        _state['current_index'] = i
                        _state['sent'] = i + 1
                    time.sleep(delay)
                # Flash all dots, then clear
                with _lock:
                    _state['current_cell'] = 0x3F
                time.sleep(delay * 1.5)
                with _lock:
                    _state['current_cell'] = 0
            else:
                with serial.Serial(port, 115200, timeout=1.0) as s:
                    time.sleep(1.5)
                    s.write(b'T\n')
                    # Monitor response for 4 seconds
                    t_end = time.time() + 4.0
                    while time.time() < t_end:
                        if s.in_waiting:
                            line = s.readline().decode('utf-8', errors='ignore').strip()
                            if 'PASSED' in line:
                                break
                        time.sleep(0.1)
        except Exception as e:
            with _lock:
                _state['error'] = str(e)
        finally:
            with _lock:
                _state['running'] = False
                _state['mode'] = 'idle'

    threading.Thread(target=run_test, daemon=True).start()
    return {'ok': True, 'started': True, 'port': port}


def send(port: str, cells: List[int], delay: float = 1.0, baud: int = 115200):
    """Stream a sequence of Braille cells (integers 0..63) to hardware or virtual simulator."""
    if not port:
        raise ValueError('No serial port selected')
    if port != VIRTUAL_PORT and serial is None:
        raise RuntimeError('pyserial is not installed (pip install pyserial)')

    cells = [int(c) & 0x3F for c in cells][:1000]
    if not cells:
        return

    with _lock:
        if _state['running']:
            raise RuntimeError('A transfer is already running')
        _state.update(
            running=True, sent=0, total=len(cells), current_cell=0, current_index=0,
            port=port, error=None, stop=False, mode='stream'
        )

    def work():
        try:
            if port == VIRTUAL_PORT:
                for idx, c in enumerate(cells):
                    with _lock:
                        if _state['stop']:
                            break
                        _state['current_cell'] = c
                        _state['current_index'] = idx
                    t_end = time.time() + max(0.15, delay)
                    while time.time() < t_end:
                        with _lock:
                            if _state['stop']:
                                break
                        time.sleep(0.04)
                    with _lock:
                        _state['sent'] += 1
            else:
                with serial.Serial(port, baud, timeout=0.1) as s:
                    time.sleep(1.5)  # ESP32 auto-resets on DTR toggle
                    for idx, c in enumerate(cells):
                        with _lock:
                            if _state['stop']:
                                break
                            _state['current_cell'] = c
                            _state['current_index'] = idx
                        # Send framed cell byte
                        s.write(bytes([ord('C'), c]))
                        t_end = time.time() + max(0.15, delay)
                        while time.time() < t_end:
                            with _lock:
                                if _state['stop']:
                                    break
                            # Check for hardware tactile button push
                            if s.in_waiting:
                                line = s.readline().decode('utf-8', errors='ignore').strip()
                                if line == 'NEXT':
                                    break
                            time.sleep(0.04)
                        with _lock:
                            _state['sent'] += 1
                    # Clear cell at completion
                    s.write(b'R\n')
        except Exception as e:
            with _lock:
                _state['error'] = str(e)
        finally:
            with _lock:
                _state['running'] = False
                _state['mode'] = 'idle'

    threading.Thread(target=work, daemon=True).start()
