import asyncio
import websockets
import redis
import json
import uuid
import logging
import argparse
import sys
from subprocess import Popen

parser = argparse.ArgumentParser(
                    prog='Daisy-Chain Server',
                    description='Daisy-Chain RTSP yayın sistem sunucusu.'
                )
parser.add_argument('--ipv4', dest='ipv4', help='Ana sunucunun ipv4 adresi.', default='127.0.0.1')
parser.add_argument('--max-member', dest='max_member', help='Grupların kaç istemciden oluşacağı.', default=5)
args = parser.parse_args()


logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO)
logger = logging.getLogger('daisychain')

def get_groups():
    groups = redis_client.get("groups")
    if groups == None:
        return None
    return json.loads(groups)


def get_clients():
    clients = redis_client.get("clients")
    if clients == None:
        return None
    return json.loads(clients)


async def remove_client(websocket):
    active_clients = get_clients()
    active_groups = get_groups()
    client_ip_to_remove = websocket.remote_address[0]

    updated_clients_data = [client for client in active_clients if client["ip_address"] != client_ip_to_remove]

    for group in active_groups:
        if client_ip_to_remove in group["members"]:
            group["members"].remove(client_ip_to_remove)
            group["member_count"] = len(group["members"])
            if group["member_count"] == 0:
                active_groups.remove(group)
    
    redis_client.set("clients", json.dumps(updated_clients_data))
    redis_client.set("groups", json.dumps(active_groups))


async def add_client(websocket):
    active_clients = get_clients()

    if active_clients == None:
        active_clients = []

    assigned_group = await client_to_group(websocket)
    client_data = {
        "ip_address": websocket.remote_address[0],
        "group_id": assigned_group["id"],
        "streamer": assigned_group["streamer"], # Boolean, bu değere göre RTSP sunucu başlatılacak.
    }

    active_clients.append(client_data)
    redis_client.set("clients", json.dumps(active_clients))


async def client_to_group(websocket):
    active_groups = get_groups()

    if active_groups == None:
        group_details = await create_group(websocket)
        return {"id": group_details["id"], "streamer": websocket.remote_address[0] == group_details["admin"]}

    available_groups = [group for group in active_groups if group["member_count"] < MAX_GROUP_MEMBER]

    if len(available_groups) == 0:
        group_details = await create_group(websocket)
        return {"id": group_details["id"], "streamer": websocket.remote_address[0] == group_details["admin"]}

    group_details = available_groups[0]
    group_details["members"].append(websocket.remote_address[0])
    group_details["member_count"] += 1
    redis_client.set("groups", json.dumps(available_groups))
    return {"id": group_details["id"], "streamer": websocket.remote_address[0] == group_details["admin"]}


async def create_group(websocket):
    active_groups = get_groups()
    if active_groups == None:
        active_groups = []

    new_group_id = str(uuid.uuid4())
    get_stream_from = get_available_streamer(active_groups)
    group_data = {
        "id": new_group_id,
        "admin": websocket.remote_address[0],
        "get_stream_from": get_stream_from["ip"],
        "members": [websocket.remote_address[0]],
        "member_count": 1,
        "stream_to_group": None
    }

    active_groups.append(group_data)
    redis_client.set("groups", json.dumps(active_groups))
    
    if get_stream_from["group_id"] != None:
        set_stream_to_group(get_stream_from["group_id"], new_group_id)

    await websocket.send(json.dumps({"streamer": True, "get_stream_from": get_stream_from["ip"]}))
    return {"id": group_data["id"], "admin": group_data["admin"]}

def set_stream_to_group(group_id, created_group_id):
    active_groups = get_groups()
    if active_groups is None:
        return

    for group in active_groups:
        if group["id"] == group_id:
            group["stream_to_group"] = created_group_id

    redis_client.set("groups", json.dumps(active_groups))

def get_available_streamer(active_groups):
    available_groups = [group for group in active_groups if group["stream_to_group"] == None]

    if len(available_groups) == 0:
        return {"ip": DEFAULT_SERVER_IP, "group_id": None}

    return {"ip": available_groups[0]["admin"], "group_id": available_groups[0]["id"]}


async def server(websocket, path):
    print("Bağlantı kuruldu: ", websocket.remote_address[0])
    await add_client(websocket)
    try:
        while True:
            data = await websocket.recv()
            print(f"Gelen veri: {data}")
    except websockets.exceptions.ConnectionClosed:
        await remove_client(websocket)


if __name__ == '__main__':
    # Redis bağlantısını oluştur
    redis_host = 'localhost'
    redis_port = 6379
    redis_db = 0
    redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db)
    try:
        redis_client.client_list()
    except redis.ConnectionError:
        sys.exit("Redis connection failed, make sure redis is running.")

    logger.info("Redis connection succeeded.")
    redis_client.delete("clients", "groups")
    MAX_GROUP_MEMBER = args.max_member
    DEFAULT_SERVER_IP = args.ipv4

    start_server = websockets.serve(server, DEFAULT_SERVER_IP, 8765)
    logger.info("Websocket server listening on " + DEFAULT_SERVER_IP + ":8765 (This IP should be IPv4, not 127.0.0.1)")

    try:
        mediamtx_server = Popen(["mediamtx/mediamtx", "mediamtx/mediamtx.yml"]) # Start RTSP server over mediamtx.
        stream_client = Popen(["stream-client.exe"])
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        mediamtx_server.terminate()
        mediamtx_server.wait()
        stream_client.terminate()
        stream_client.wait()