
import {
    FilesetResolver,
    HandLandmarker
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14";

const $ = (s) => document.querySelector(s);

const video = $("#webcam");
const cursor = $("#airCursor");
const startButton = $("#startButton");

let handLandmarker = null;
let cameraStream = null;
let running = false;
let active = false;
let wasPinching = false;
let lastGesture = "";
let lastActionTime = 0;
let smoothX = window.innerWidth / 2;
let smoothY = window.innerHeight / 2;
let lastVideoTime = -1;

function clockTick() {
    $("#clock").textContent = new Date().toLocaleTimeString("en-IN", {
        hour12: false
    });
}
clockTick();
setInterval(clockTick, 1000);

function toast(message) {
    const el = $("#toast");
    el.textContent = message;
    el.classList.remove("show");
    void el.offsetWidth;
    el.classList.add("show");
}

function logCommand(message) {
    $("#commandMessage").textContent = message;
}

function setActive(value) {
    active = value;
    $("#systemStatus").textContent = active ? "AIR CONTROL ACTIVE" : "SYSTEM PAUSED";
    $("#mainTitle").innerHTML = active
        ? "AIR CONTROL ENGAGED<span>.</span>"
        : "MOVE YOUR HAND<span>.</span>";

    $("#mainMessage").textContent = active
        ? "Point with your index finger and pinch to select."
        : "Show an open palm to activate the interface.";

    $("#pointerModule").textContent = active ? "ACTIVE" : "PAUSED";
    cursor.classList.toggle("visible", active);
    $("#waveform").classList.toggle("active", active);

    if (active) {
        toast("AIR CONTROL ACTIVATED");
        logCommand("Interface activated by hand gesture.");
    } else {
        toast("INTERACTION PAUSED");
        logCommand("Interaction paused.");
    }
}

function distance(a, b) {
    return Math.hypot(a.x - b.x, a.y - b.y);
}

function getGesture(lm) {
    // Landmark pairs: fingertip and middle finger joint.
    const fingerPairs = [
        [8, 6],   // index
        [12, 10], // middle
        [16, 14], // ring
        [20, 18]  // little
    ];

    const extended = fingerPairs.map(([tip, joint]) =>
        lm[tip].y < lm[joint].y
    );

    const extendedCount = extended.filter(Boolean).length;
    const pinchDistance = distance(lm[4], lm[8]);
    const pinching = pinchDistance < 0.055;

    // Gesture priority matters: detect pinch before open palm.
    if (pinching) return "PINCH";
    if (extendedCount >= 4) return "OPEN PALM";
    if (extendedCount === 0 || (extendedCount === 1 && extended[0] === false)) {
        return "FIST";
    }
    if (extended[0] && extendedCount === 1) return "POINTING";

    return "TRACKING";
}

function moveCursor(lm) {
    // Mirror the X position because the webcam preview is mirrored.
    const targetX = (1 - lm[8].x) * window.innerWidth;
    const targetY = lm[8].y * window.innerHeight;

    // Smooth out small tracking jitters.
    smoothX += (targetX - smoothX) * 0.35;
    smoothY += (targetY - smoothY) * 0.35;

    cursor.style.left = `${smoothX}px`;
    cursor.style.top = `${smoothY}px`;

    $("#cursorX").textContent = Math.round(smoothX);
    $("#cursorY").textContent = Math.round(smoothY);

    // Make the hologram react to the hand.
    const rect = $("#orbArea").getBoundingClientRect();
    const nx = (smoothX - (rect.left + rect.width / 2)) / rect.width;
    const ny = (smoothY - (rect.top + rect.height / 2)) / rect.height;

    $("#orbArea").style.transform =
        `translate(${Math.max(-18, Math.min(18, nx * 28))}px, ` +
        `${Math.max(-18, Math.min(18, ny * 28))}px)`;

    $("#orb").style.filter =
        `hue-rotate(${Math.round(nx * 35)}deg) brightness(${1 + Math.min(0.25, Math.abs(ny) * 0.3)})`;
}

function triggerAirClick() {
    const now = performance.now();

    // Avoid accidental repeated clicks while holding the pinch.
    if (now - lastActionTime < 700) return;
    lastActionTime = now;

    const target = document.elementFromPoint(smoothX, smoothY);
    const button = target?.closest("button");

    if (button && !button.disabled) {
        button.click();
        cursor.classList.add("pinch");
        setTimeout(() => cursor.classList.remove("pinch"), 250);
        toast("AIR CLICK");
        logCommand(`Air selection: ${button.innerText.trim() || "control"}`);
    } else {
        // Pinching on empty space still creates a holographic pulse.
        $("#orb").animate(
            [
                { transform: "scale(1)", filter: "brightness(1)" },
                { transform: "scale(1.12)", filter: "brightness(1.8)" },
                { transform: "scale(1)", filter: "brightness(1)" }
            ],
            { duration: 400 }
        );
        toast("HOLOGRAM PULSE");
    }
}

function updateGesture(lm) {
    const gesture = getGesture(lm);

    $("#gestureStatus").textContent = gesture;
    $("#handStatus").textContent = "DETECTED";
    $("#cameraCaption").textContent = `Current gesture: ${gesture}`;

    if (gesture !== lastGesture) {
        logCommand(`Gesture detected: ${gesture}`);
        lastGesture = gesture;
    }

    // An open palm activates or resumes the interface.
    if (gesture === "OPEN PALM" && !active) {
        setActive(true);
    }

    // A fist pauses all air interaction.
    if (gesture === "FIST" && active) {
        setActive(false);
    }

    if (active) {
        moveCursor(lm);
        cursor.classList.add("visible");
    }

    if (active && gesture === "PINCH" && !wasPinching) {
        triggerAirClick();
    }

    wasPinching = gesture === "PINCH";
}

function renderLoop() {
    if (!running || !handLandmarker) return;

    if (video.readyState >= 2 && video.currentTime !== lastVideoTime) {
        lastVideoTime = video.currentTime;

        try {
            const result = handLandmarker.detectForVideo(video, performance.now());
            const hand = result.landmarks?.[0];

            if (hand) {
                updateGesture(hand);
            } else {
                $("#handStatus").textContent = "NOT DETECTED";
                $("#gestureStatus").textContent = "—";
                $("#cameraCaption").textContent = "Show your hand inside the camera view.";

                // Hide the cursor if the hand leaves the camera view.
                cursor.classList.remove("visible");
                wasPinching = false;
                lastGesture = "";
            }
        } catch (error) {
            console.error("Hand tracking error:", error);
        }
    }

    requestAnimationFrame(renderLoop);
}

async function startCamera() {
    startButton.disabled = true;
    startButton.textContent = "INITIALIZING...";
    $("#cameraMessage").textContent = "Loading hand-tracking model...";
    logCommand("Initializing vision engine...");

    try {
        if (!navigator.mediaDevices?.getUserMedia) {
            throw new Error("Camera access requires localhost or HTTPS.");
        }

        // Load the vision runtime.
        const vision = await FilesetResolver.forVisionTasks(
            "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm"
        );

        handLandmarker = await HandLandmarker.createFromOptions(vision, {
            baseOptions: {
                modelAssetPath:
                    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
                delegate: "GPU"
            },
            runningMode: "VIDEO",
            numHands: 1,
            minHandDetectionConfidence: 0.6,
            minHandPresenceConfidence: 0.6,
            minTrackingConfidence: 0.6
        });

        // Request webcam permission.
        cameraStream = await navigator.mediaDevices.getUserMedia({
            audio: false,
            video: {
                facingMode: "user",
                width: { ideal: 640 },
                height: { ideal: 480 }
            }
        });

        video.srcObject = cameraStream;
        await video.play();

        running = true;
        $("#visionModule").textContent = "ONLINE";
        $("#gestureModule").textContent = "ONLINE";
        $("#cameraMessage").textContent = "Camera connected. Show an open palm.";
        $("#systemStatus").textContent = "VISION ONLINE";
        startButton.textContent = "✓ CAMERA CONNECTED";
        $("#cameraCaption").textContent = "Waiting for your hand...";

        logCommand("Vision engine online. Waiting for open palm.");
        toast("VISION MODULE ONLINE");

        renderLoop();
    } catch (error) {
        console.error(error);
        $("#cameraMessage").textContent =
            `Could not start: ${error.message}. Check camera permission and internet.`;
        $("#systemStatus").textContent = "INITIALIZATION FAILED";
        startButton.disabled = false;
        startButton.textContent = "↻ RETRY CAMERA";
        toast("CAMERA INITIALIZATION FAILED");
    }
}

startButton.addEventListener("click", startCamera);

// Dashboard controls can be selected with a real mouse or an air pinch.
document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => {
        const action = button.dataset.action;

        document.querySelectorAll(".action-card").forEach((card) => {
            card.classList.toggle("selected", card === button);
        });

        switch (action) {
            case "SCAN":
                $("#orb").animate(
                    [
                        { filter: "brightness(1)" },
                        { filter: "brightness(2) hue-rotate(80deg)" },
                        { filter: "brightness(1)" }
                    ],
                    { duration: 1000 }
                );
                logCommand("Visual scan complete. No external scanning performed.");
                toast("VISUAL SCAN COMPLETE");
                break;

            case "SHIELD":
                $("#orb").classList.toggle("shield-mode");
                document.body.classList.toggle("shield-mode");
                logCommand("Holographic shield visual toggled.");
                toast("SHIELD VISUAL TOGGLED");
                break;

            case "ENERGY":
                $("#orb").animate(
                    [
                        { transform: "scale(1)" },
                        { transform: "scale(1.18)" },
                        { transform: "scale(1)" }
                    ],
                    { duration: 650 }
                );
                $("#orbArea").animate(
                    [{ filter: "brightness(1)" }, { filter: "brightness(1.7)" }, { filter: "brightness(1)" }],
                    { duration: 650 }
                );
                logCommand("Core energy visual boost activated.");
                toast("CORE ENERGY BOOST");
                break;

            case "RESET":
                $("#orbArea").style.transform = "";
                $("#orb").style.filter = "";
                document.body.classList.remove("shield-mode");
                $("#orb").classList.remove("shield-mode");
                document.querySelectorAll(".action-card").forEach((card) => card.classList.remove("selected"));
                logCommand("Holographic interface visuals reset.");
                toast("INTERFACE RESET");
                break;
        }
    });
});

// Shield mode adds a stronger glow while active.
const shieldStyle = document.createElement("style");
shieldStyle.textContent = `
  body.shield-mode .orb {
    box-shadow: inset 0 0 25px #8fffff, 0 0 35px #46edff,
      0 0 90px #178bff, 0 0 150px #178bff99;
  }
  body.shield-mode .orbit { border-width: 2px; }
`;
document.head.appendChild(shieldStyle);

window.addEventListener("beforeunload", () => {
    running = false;
    cameraStream?.getTracks().forEach((track) => track.stop());
    handLandmarker?.close();
});
