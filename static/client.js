start_btn = document.getElementById('start')
stop_btn =document.getElementById('stop')
statusField = document.getElementById('status')

let pc = null;
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

  //create data chanel
  dc = pc.createDataChannel('result')
  //envent handler
  dc.onclose = function() {
    clearInterval(dcInterval)
    console.log('Closed data channel')
    btn_show_start()
  }

  dc.onopen = function() {
    console.log("Open data channel")
  }

  dc.onmessage = function (messageEvent) {
    statusField.innerText = "Listening .... !"
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
    //ICE gathering
    await pc.setLocalDescription(offer);  
    //gathering network information
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

    //Gatherting coompleted
    const offDescription = pc.localDescription;
    console.log("Offer SDP: ", offDescription.sdp);
    //send offer to server
    const answer = await sendOffer(offDescription)
    //change status satusField
    pc.setRemoteDescription(answer)

  }

  const processMedia = async (constraints) => {
    try {
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


