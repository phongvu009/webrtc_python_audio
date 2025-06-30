import os
import ssl
from aiohttp import web
import json

from aiortc import RTCPeerConnection, RTCSessionDescription

from pathlib import Path
#import logging
#use loguru 
from loguru import logger
import sys


# get path
ROOT = Path(__file__).parent

logger.remove() # Remove all existing handlers before adding new ones
#default log level
logger.add(sys.stderr, level="DEBUG")
#custom format
#logger.add(sys.stderr, level="DEBUG", format="<green>{time}</green> | {level} | {message}  ")


# or provide the full path to them.
HOME_DIR = os.path.expanduser("~")
SSL_CERT_FILE = os.path.join(HOME_DIR, "localhost+1.pem")
SSL_KEY_FILE = os.path.join(HOME_DIR, "localhost+1-key.pem")


async def index(request):
    childlogger = logger.bind(name="index")
    childlogger.info("Serving index.html")
    content = open(str(ROOT / "static" / "index.html")).read()
    return web.Response(content_type="text/html", text=content)

#handle offer request
async def offer(request):
    logger.info("Received offer request")
    try:
        params = await request.json()
        logger.debug(f"Offer parameters: {params}")
        #Serialize offer
        if 'sdp' not in params or 'type' not in params:
            logger.error("Missing 'sdp' or 'type' in offer parameters")
            return web.Response(status=400, text="Missing 'sdp' or 'type' in offer parameters")
        
        offer = RTCSessionDescription(sdp=params['sdp'], type=params['type'])
        #logger.trace(f"Offer SDP: {offer.sdp}, type: {offer.type}")
        logger.trace(f"type is : {offer.type}")
        #create peer connection
        pc = RTCPeerConnection()
        
        #data channel
        @pc.on("datachannel")
        def on_datachannel(channel):
            logger.info(f"Data channel created: {channel.label}")

            @channel.on("message")
            def on_message(message):
                logger.info(f"Data channel message: {message}")
                #send message back to client
                channel.send(f"Server received: {message}")


        await pc.setRemoteDescription(offer)
        #generate answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        logger.info("Answer created successfully !!!")
        return web.Response(
            content_type='application/json',
            text = json.dumps({
                'sdp': pc.localDescription.sdp,
                'type': pc.localDescription.type
            })
        )
    except Exception as e:
        logger.error(f"An error occurred while processing the offer: {e}")
        return web.Response(status=500, text="Internal Server Error")

if __name__ == "__main__":
    #logging.basicConfig(level=logging.DEBUG)
    
    # add SSL context
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(SSL_CERT_FILE, SSL_KEY_FILE)

    app = web.Application()

    # add route, default to load html web page - Step 1
    app.router.add_get("/", index)
    # add static dir
    app.router.add_static("/static/", path=ROOT / "static", name="static")
    # add offer enpoint handler
    app.router.add_post("/offer", offer)

    # run server - Step 0
    web.run_app(app, host="0.0.0.0", port=8091, ssl_context=ssl_context)
