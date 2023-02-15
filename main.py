import asyncio
import uvicorn
from fastapi import FastAPI
from argparse import ArgumentParser
from pydantic import BaseModel
from typing import Union
from xashlib import get_servers, query_servers, Address

parser = ArgumentParser(description = "Xash api")
parser.add_argument("--ip", type = str, default = "127.0.0.1", help = "Adress of api")
parser.add_argument("--port", type = int, default = 5000, help = "Port of api")

ms_list = [Address(**{"addr":"ms.xash.su","port":27010}),
        Address(**{"addr":"ms2.xash.su","port":27010}),
        Address(**{"addr":"ms.csat.ml","port":27010})]

class Options(BaseModel):
    nat: bool = 0
    timeout: float = 0.5

app = FastAPI()

@app.get("/servers")
@app.get("/servers/{game}")
@app.post("/servers")
@app.post("/servers/{game}")
async def handle_servers(options: Options = Options(), game: Union[str, None] = "cstrike"):
    servers = {"servers":[]}
    ip_list = await get_servers(game, options.nat, ms_list[0], options.timeout)
    if ip_list:
        coros = [query_servers(i, servers, options) for i in ip_list]
        await asyncio.gather(*coros)
    return servers

@app.get("/iplist")
@app.get("/iplist/{game}")
@app.post("/iplist")
@app.post("/iplist/{game}")
async def handle_iplist(options: Options = Options(), game: Union[str, None] = "cstrike"):
    servers = {"ips":[]}
    ip_list = await get_servers(game, options.nat, ms_list[0], options.timeout)
    if ip_list:
        [servers["ips"].append(i) for i in ip_list]
    
    return servers
    
if __name__ == "__main__":
    args = parser.parse_args()
    uvicorn.run("main:app", host = args.ip, port = args.port, log_level = "info")