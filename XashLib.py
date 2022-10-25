import struct
import asyncio
import asyncio_dgram
from pydantic import BaseModel
import traceback

class Address(BaseModel):
    addr: str
    port: int
    def __str__(self) -> str:
        return f"{self.addr}:{self.port}"

def unpack_byte(data: bytes):
    return struct.unpack('<B', data[:1])[0], data[1:]
def unpack_short(data: bytes):
    return struct.unpack('<h', data[:2])[0], data[2:]
def unpack_long(data: bytes):
    return struct.unpack('<l', data[:4])[0], data[4:]
def unpack_longlong(data: bytes):
    return struct.unpack('<Q', data[:8])[0], data[8:]
def unpack_float(data: bytes):
    return struct.unpack('<f', data[:4])[0], data[4:]
def unpack_string(data: bytes):
    return data.split(b'\x00', 1)

async def send_packet(ip, port, msg, timeout: float) -> bytes | None:
    stream = await asyncio_dgram.connect((ip, port))
    await stream.send(msg)
    try:
        data, _ = await asyncio.wait_for(stream.recv(), timeout=timeout)
    except asyncio.TimeoutError:
        data = None
    finally:
        stream.close()

    return data

async def get_servers(gamedir:str, nat:bool, ms:Address, timeout:float) -> list[Address]:
    servers = []
    QUERY = b'1\xff0.0.0.0:0\x00\\nat\\%b\\gamedir\\%b\\clver\\0.19.2\x00' % (str(nat).encode(), gamedir.encode())

    data = await send_packet(ms.addr, ms.port, QUERY, timeout)

    if not data:
        return None

    data = data[6:]
    for i in range(0, len(data), 6):
        ip1, ip2, ip3, ip4, port = struct.unpack(b">BBBBH", data[i:i+6])
        servers.append(Address(addr=f"{ip1}.{ip2}.{ip3}.{ip4}", port=port))

    servers.pop() #Last server is 0.0.0.0
    return servers

async def query_servers(target:Address, serverdict, options) -> None:
    QUERY_SERVER = b'\xff\xff\xff\xffTSource'
    raw = await send_packet(target.addr, target.port, QUERY_SERVER, options.timeout)

    if not raw:
        return # Server didn't reply.

    result={}

    connless_marker, raw = unpack_long(raw)
    if not connless_marker == -1:
        return #raise Exception("Invalid connectionless packet marker!")

    engine_type, raw = unpack_byte(raw)
    try:
        if chr(engine_type) == 'I':  #Source format (<= 0.19.x)
            result['protocol_ver'], raw = unpack_byte(raw)
            result['hostname'], raw = unpack_string(raw)
            result['map'], raw = unpack_string(raw)
            result['gamedir'], raw = unpack_string(raw)
            result['gamedesc'], raw = unpack_string(raw)
            result['appid'], raw = unpack_short(raw)
            result['numplayers'], raw = unpack_byte(raw)
            result['maxplayers'], raw = unpack_byte(raw)
            result['numbots'], raw = unpack_byte(raw)
            result['dedicated'], raw = unpack_byte(raw)
            result['os'], raw = unpack_byte(raw)
            result['passworded'], raw = unpack_byte(raw)
            result['secure'], raw = unpack_byte(raw)
            result['os'] = chr(result['os'])
            if result['os'].lower() == 'l':
                os = "Linux"
            elif result['os'].lower() == 'w':
                os = "Windows"
            elif result['os'].lower() == 'm':
                os = "Mac OS"
            else:
                os = "Unknown OS"

        elif chr(engine_type) == 'm': #GoldSource format (>= 0.20.x)
            result['address'], raw = unpack_string(raw)
            result['hostname'], raw = unpack_string(raw)
            result['map'], raw = unpack_string(raw)
            result['gamedir'], raw = unpack_string(raw)
            result['gamedesc'], raw = unpack_string(raw)
            result['numplayers'], raw = unpack_byte(raw)
            result['maxplayers'], raw = unpack_byte(raw)
            result['protocol_ver'], raw = unpack_byte(raw)
            result['servertype'], raw = unpack_byte(raw)
            result['os'], raw = unpack_byte(raw)
            result['is_mod'], raw = unpack_byte(raw)
            if result['is_mod'] == 1:
                result['game_url'], raw = unpack_string(raw)
                result['update_url'], raw = unpack_string(raw)
                result['null'], raw = unpack_byte(raw)
                result['mod_ver'], raw = unpack_long(raw)
                result['mod_size'], raw = unpack_long(raw)
                result['mod_type'], raw = unpack_byte(raw)
                result['dll_type'], raw = unpack_byte(raw)
            result['secure'], raw = unpack_byte(raw)
            result['bots'], raw = unpack_byte(raw)
            result['os'] = chr(result['os'])
            result['servertype'] = chr(result['servertype'])
            if result['os'].lower() == 'l':
                os = "Linux"
            elif result['os'].lower() == 'w':
                os = "Windows"
            elif result['os'].lower() == 'm':
                os = "Mac OS"
            else:
                os = "Unknown OS"

        else:
            return #raise Exception("Invalid engine type!")

        server = {
            "addr": f"{target.addr}",
            "port": target.port,
            "hostname": result['hostname'].decode('utf-8'),
            "map": f"{result['map'].decode('utf-8')}",
            "players": result['numplayers'],
            "maxplayers": result['maxplayers'],
            "gamedir": f"{result['gamedir'].decode('utf-8')}",
            "gamedesc": f"{result['gamedesc'].decode('utf-8')}",
            "os": os,
            "version": result['protocol_ver']
        }
        serverdict["servers"].append(server.copy())

    except Exception:
        traceback.print_exc()
        pass
