start_btn = document.getElementById('start')
stop_btn =document.getElementById('stop')
statusField = document.getElementById('status')

let pc;
let dc; // Data Channel
var dcInterval = null;

function btn_show_stop() {
  //add class to not show start button
  start_btn.classList.add('d-none')
  //
  stop_btn.classList.remove('d-none')
}

function btn_show_start() {
  stop_btn.classList.add('d-none')
  //
  start_btn.classList.remove('d-none')
}


//click on stop button - Step 1
function stop() {
  btn_show_start()
}



//click on start button  - Step 1
function start() {
  btn_show_stop();
  statusField.innerText = 'Connecting .... '
  var config = {
    sdpSemantics: 'unified-plan'
  }
  console.log("create Peer Connection")
  //create peer connection
  pc = new RTCPeerConnection(config)

  //Set up data channel: open, closed, receive messages
  //create data chanel named 'result'
  dc = pc.createDataChannel('chat room 1')
  //envent handler for data channel
  dc.onclose = function() {
    clearInterval(dcInterval)
    console.log('Closed data channel')
    btn_show_start()
  }
  //
  dc.onopen = function() {
    console.log("Open data channel")
    //send message to server
    dc.send("Hello from client")
  }

  dc.onmessage = function (messageEvent) {
    statusField.innerText = "Listening .... !"
    console.log("Received message from server: ", messageEvent.data);
  }

//======================== Hand Shake ====================
  const sendOffer = async(offerDescription) => {
    const response = await fetch('/offer', {
      method : 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ 'sdp': offerDescription.sdp, 'type': offerDescription.type })
    })
    return response.json()
}

  const negotiate = async () => {
    console.log("Start negotiating !!!")

    const offer = await pc.createOffer();

    // on event: ICE candidate - collect both TCP , UDP  port available
    pc.onicecandidate = async (event) => {
      if (event.candidate) {
        console.log("New ICE candidate: ", event.candidate);
        
      }
    }
    //ICE gathering
    await pc.setLocalDescription(offer);  
    //gathering Public IP and port from STUN server.
    await new Promise( (resolve) =>{
      if (pc.iceGatheringState === 'complete') {
        resolve();
      } else {
          const checkState= () => {
            if (pc.iceGatheringState === 'complete') {
              pc.removeEventListener('icegatheringstatechange', checkState);
              resolve();
              }
            }
          //keep checking until state is complete - infinite loop
          pc.addEventListener('icegatheringstatechange', checkState);
        }
    })

    //Gatherting completed
    const offDescription = pc.localDescription;
    console.log("Offer SDP:\r\n", offDescription.sdp);
    //send offer to server
    const answer = await sendOffer(offDescription)
    //change status satusField
    pc.setRemoteDescription(answer)
    console.log("got answer from server")
    console.log("Answer SDP:\r\n", answer.sdp);

    //Connection status Event Handler 

    pc.oniceconnectionstatechange = async () => {
      console.log("ICE connection state: ", pc.iceConnectionState);
      if (pc.iceConnectionState === 'connected') {
        console.log("Connected to server");
        statusField.innerText = "Connected !"
      }
    }

  } 

  const processMedia = async (constraints) => {
    try {
      //ask for media devices permission
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      stream.getTracks().forEach(track => pc.addTrack(track, stream));
      return negotiate(); // send offer
    } catch (err) {
      console.error('Error accessing media devices.', err);
    }
  }
  
  // position to load this is matter
  //auto load audio when first load website
  var constraints = {
    audio: true,
    video: false,
  }

  processMedia(constraints);

  
}

