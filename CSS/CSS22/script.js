
import * as THREE from
  "https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.module.js";

import { OrbitControls } from
  "https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/controls/OrbitControls.js";

// =====================================
// 1. SCENE
// =====================================
const container = document.getElementById("scene-container");

const scene = new THREE.Scene();
scene.background = new THREE.Color("#09182d");
scene.fog = new THREE.Fog("#09182d", 12, 28);

const camera = new THREE.PerspectiveCamera(
  40, container.clientWidth / container.clientHeight, 0.1, 100
);
camera.position.set(0, 3.5, 10);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(container.clientWidth, container.clientHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.25;
container.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1.8, 0);
controls.enableDamping = true;
controls.minDistance = 6;
controls.maxDistance = 15;
controls.maxPolarAngle = Math.PI / 2.05;

// =====================================
// 2. LIGHTS
// =====================================
scene.add(new THREE.HemisphereLight(0xc8e7ff, 0x17223a, 2));

const light = new THREE.DirectionalLight(0xffffff, 3);
light.position.set(-4, 8, 6);
light.castShadow = true;
light.shadow.mapSize.set(1024, 1024);
scene.add(light);

const glow = new THREE.PointLight(0x168bff, 30, 15);
glow.position.set(3, 4, -2);
scene.add(glow);

// =====================================
// 3. MATERIALS AND SHAPES
// =====================================
const mat = (color, roughness = 0.4, metalness = 0) =>
  new THREE.MeshStandardMaterial({ color, roughness, metalness });

const blue = mat("#0785e9");
const white = mat("#fffaf0");
const black = mat("#141a26");
const red = mat("#f62d40");
const gold = mat("#ffcc43", 0.25, 0.35);
const silver = mat("#d1e0ed", 0.25, 0.4);

function ball(parent, name, x, y, z, sx, sy, sz, material) {
  const mesh = new THREE.Mesh(
    new THREE.SphereGeometry(1, 32, 24), material
  );
  mesh.name = name;
  mesh.position.set(x, y, z);
  mesh.scale.set(sx, sy, sz);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}

function tube(parent, points, material, radius = 0.018) {
  const curve = new THREE.CatmullRomCurve3(
    points.map(p => new THREE.Vector3(...p))
  );
  const mesh = new THREE.Mesh(
    new THREE.TubeGeometry(curve, 24, radius, 8, false),
    material
  );
  parent.add(mesh);
  return mesh;
}

// =====================================
// 4. FLOOR AND STARS
// =====================================
const floor = new THREE.Mesh(
  new THREE.PlaneGeometry(200, 200),
  mat("#142a43", 0.85)
);
floor.rotation.x = -Math.PI / 2;
floor.position.y = -0.05;
floor.receiveShadow = true;
scene.add(floor);

const platform = new THREE.Mesh(
  new THREE.CircleGeometry(1.8, 64),
  new THREE.MeshBasicMaterial({
    color: "#10416a", transparent: true, opacity: 0.65
  })
);
platform.rotation.x = -Math.PI / 2;
platform.position.y = -0.025;
scene.add(platform);

const ring = new THREE.Mesh(
  new THREE.TorusGeometry(1.5, 0.018, 8, 80),
  new THREE.MeshBasicMaterial({ color: "#35c7ff" })
);
ring.rotation.x = Math.PI / 2;
ring.position.y = 0.005;
scene.add(ring);

const starPositions = [];
for (let i = 0; i < 400; i++) {
  starPositions.push(
    (Math.random() - 0.5) * 35,
    Math.random() * 12 + 1,
    -5 - Math.random() * 20
  );
}

const starGeo = new THREE.BufferGeometry();
starGeo.setAttribute(
  "position", new THREE.Float32BufferAttribute(starPositions, 3)
);

scene.add(new THREE.Points(
  starGeo,
  new THREE.PointsMaterial({
    color: "#a9dcff", size: 0.045, transparent: true, opacity: 0.8
  })
));

const shadow = new THREE.Mesh(
  new THREE.CircleGeometry(0.75, 32),
  new THREE.MeshBasicMaterial({
    color: "#020712", transparent: true, opacity: 0.35
  })
);
shadow.rotation.x = -Math.PI / 2;
shadow.position.y = 0.01;
scene.add(shadow);

// =====================================
// 5. DORAEMON
// =====================================
const doraemon = new THREE.Group();
scene.add(doraemon);

const body = new THREE.Group();
doraemon.add(body);

// Body and tummy
ball(body, "body", 0, 1.45, 0, 0.72, 0.82, 0.55, blue);
ball(body, "tummy", 0, 1.42, 0.43, 0.51, 0.57, 0.19, white);

// Head
ball(body, "head", 0, 2.92, 0, 0.98, 0.94, 0.82, blue);
ball(body, "face", 0, 2.82, 0.57, 0.79, 0.70, 0.30, white);

// Ears
ball(body, "earL", -0.87, 3.38, 0, 0.18, 0.24, 0.16, blue);
ball(body, "earR", 0.87, 3.38, 0, 0.18, 0.24, 0.16, blue);

// Eyes
ball(body, "eyeL", -0.23, 3.20, 0.83, 0.17, 0.24, 0.10, white);
ball(body, "eyeR", 0.23, 3.20, 0.83, 0.17, 0.24, 0.10, white);

const pupilL = ball(
  body, "pupilL", -0.19, 3.18, 0.92, 0.065, 0.11, 0.035, black
);
const pupilR = ball(
  body, "pupilR", 0.19, 3.18, 0.92, 0.065, 0.11, 0.035, black
);

// Nose
ball(body, "nose", 0, 2.94, 0.91, 0.12, 0.12, 0.11, red);

// Nose line
tube(body, [[0, 2.83, 0.90], [0, 2.65, 0.91]], black);

// Smile
tube(body, [
  [-0.34, 2.60, 0.83],
  [-0.18, 2.49, 0.88],
  [0, 2.46, 0.90],
  [0.18, 2.49, 0.88],
  [0.34, 2.60, 0.83]
], black, 0.022);

// Whiskers
for (const side of [-1, 1]) {
  for (let i = 0; i < 3; i++) {
    const y = 2.78 - i * 0.12;
    tube(body, [
      [side * 0.31, y, 0.84],
      [side * 0.55, y + (1 - i) * 0.04, 0.78],
      [side * 0.73, y + (1 - i) * 0.07, 0.70]
    ], black, 0.012);
  }
}

// Collar and bell
const collar = new THREE.Mesh(
  new THREE.TorusGeometry(0.53, 0.085, 12, 48),
  red
);
collar.position.set(0, 2.16, 0);
collar.rotation.x = Math.PI / 2;
collar.scale.set(1, 0.8, 1);
body.add(collar);

ball(body, "bell", 0, 2.08, 0.57, 0.17, 0.17, 0.12, gold);
ball(body, "bellHole", 0, 2.02, 0.68, 0.028, 0.025, 0.014, black);

// Pocket
ball(body, "pocket", 0, 1.40, 0.60, 0.32, 0.23, 0.07, white);

// Arms
function makeArm(side) {
  const pivot = new THREE.Group();
  pivot.position.set(side * 0.62, 1.94, 0);
  body.add(pivot);

  ball(pivot, "arm", side * 0.17, -0.23, 0.02,
    0.17, 0.32, 0.18, blue);

  ball(pivot, "hand", side * 0.21, -0.48, 0.07,
    0.17, 0.16, 0.16, white);

  return pivot;
}

function makeLeg(side) {
  const pivot = new THREE.Group();
  pivot.position.set(side * 0.29, 0.93, 0);
  body.add(pivot);

  ball(pivot, "leg", 0, -0.18, 0,
    0.19, 0.29, 0.20, blue);

  ball(pivot, "foot", 0, -0.39, 0.13,
    0.27, 0.13, 0.32, white);

  return pivot;
}

const armL = makeArm(-1);
const armR = makeArm(1);
const legL = makeLeg(-1);
const legR = makeLeg(1);

// =====================================
// 6. BAMBOO-COPTER
// =====================================
const copter = new THREE.Group();
body.add(copter);

const stem = new THREE.Mesh(
  new THREE.CylinderGeometry(0.035, 0.035, 0.20, 16),
  silver
);
stem.position.y = 4.03;
copter.add(stem);

const rotor = new THREE.Group();
rotor.position.y = 4.15;
copter.add(rotor);

ball(rotor, "hub", 0, 0, 0, 0.08, 0.05, 0.08, gold);
ball(rotor, "blade1", 0.37, 0.015, 0, 0.42, 0.025, 0.08, blue);
ball(rotor, "blade2", -0.37, 0.015, 0, 0.42, 0.025, 0.08, blue);

// =====================================
// 7. ANYWHERE DOOR
// =====================================
const portal = new THREE.Group();
scene.add(portal);
portal.position.set(1.9, 1.5, -0.4);
portal.visible = false;

const portalRing = new THREE.Mesh(
  new THREE.TorusGeometry(0.68, 0.075, 12, 48),
  new THREE.MeshStandardMaterial({
    color: "#9d54ff",
    emissive: "#7026ff",
    emissiveIntensity: 2
  })
);
portal.add(portalRing);

const portalGlass = new THREE.Mesh(
  new THREE.CircleGeometry(0.62, 48),
  new THREE.MeshBasicMaterial({
    color: "#30d8ff",
    transparent: true,
    opacity: 0.55,
    side: THREE.DoubleSide
  })
);
portalGlass.position.z = -0.05;
portal.add(portalGlass);

const doorMat = mat("#a15af2");
const doorL = new THREE.Mesh(
  new THREE.BoxGeometry(0.29, 1.1, 0.08), doorMat
);
const doorR = doorL.clone();
doorL.position.set(-0.15, 0, 0.03);
doorR.position.set(0.15, 0, 0.03);
portal.add(doorL, doorR);

// =====================================
// 8. MAGIC PARTICLES
// =====================================
const magic = new THREE.Group();
scene.add(magic);
magic.visible = false;

const particles = [];

for (let i = 0; i < 35; i++) {
  const p = new THREE.Mesh(
    new THREE.SphereGeometry(0.035 + Math.random() * 0.035, 8, 8),
    new THREE.MeshBasicMaterial({
      color: ["#64eaff", "#ffda64", "#ff72d5", "#ffffff"][i % 4]
    })
  );

  magic.add(p);

  particles.push({
    mesh: p,
    angle: Math.random() * Math.PI * 2,
    radius: 0.4 + Math.random(),
    speed: 0.5 + Math.random() * 2,
    height: Math.random() * 1.7
  });
}

// =====================================
// 9. AUTONOMOUS BRAIN
// =====================================
const actions = [
  "walk",
  "look",
  "wave",
  "jump",
  "fly",
  "door",
  "magic"
];

let currentAction = "walk";
let actionTimer = 0;
let actionDuration = 5;
let actionIndex = 0;
let actionElapsed = 0;
let time = 0;

let facing = 0;
let startX = 0;
let targetX = 0;
let startFacing = 0;
let targetFacing = 0;
let baseY = 0;
let nextActionDelay = 0;

const title = document.getElementById("characterTitle");
const message = document.getElementById("characterMessage");
const modeLabel = document.getElementById("modeLabel");

function speak(a, b) {
  title.textContent = a;
  message.textContent = b;
}

function chooseAction() {
  // Save the previous position before choosing the next action.
  startX = doraemon.position.x;
  startFacing = facing;

  const next = actions[actionIndex % actions.length];
  actionIndex++;

  // A short randomized duration keeps the sequence lively.
  currentAction = next;
  actionTimer = 0;
  actionElapsed = 0;
  actionDuration = 3.5 + Math.random() * 2.5;

  targetX = THREE.MathUtils.randFloat(-1.15, 1.15);
  targetFacing = Math.random() < 0.5 ? 0 : Math.PI;

  portal.visible = false;
  magic.visible = false;

  switch (currentAction) {
    case "walk":
      speak("Doraemon is exploring!", "Walking around the 3D world.");
      modeLabel.textContent = "● AUTONOMOUS WALK";
      break;

    case "look":
      speak("What's over there?", "Doraemon is looking around.");
      modeLabel.textContent = "● EXPLORING";
      break;

    case "wave":
      speak("Hello, friend!", "Doraemon is waving at you.");
      modeLabel.textContent = "● FRIENDLY MODE";
      break;

    case "jump":
      speak("Woohoo!", "Doraemon is jumping with joy.");
      modeLabel.textContent = "● HAPPY MODE";
      break;

    case "fly":
      speak("Take-copter activated!", "Doraemon is flying around.");
      modeLabel.textContent = "● FLYING";
      break;

    case "door":
      speak("Anywhere Door!", "A magical door is opening.");
      modeLabel.textContent = "● MAGIC GADGET";
      portal.visible = true;
      portal.scale.setScalar(0.05);
      doorL.position.x = -0.15;
      doorR.position.x = 0.15;
      break;

    case "magic":
      speak("A surprise from my pocket!", "Magic sparkles everywhere.");
      modeLabel.textContent = "● 4D POCKET";
      magic.visible = true;
      break;
  }
}

function smooth(t) {
  t = THREE.MathUtils.clamp(t, 0, 1);
  return t * t * (3 - 2 * t);
}

// Start automatically without any button click.
chooseAction();

// =====================================
// 10. ANIMATION
// =====================================
const clock = new THREE.Clock();

function animate() {
  requestAnimationFrame(animate);

  const dt = Math.min(clock.getDelta(), 0.04);
  time += dt;
  actionTimer += dt;
  actionElapsed += dt;

  if (actionTimer >= actionDuration) {
    chooseAction();
  }

  const t = smooth(actionTimer / Math.min(actionDuration, 1.8));
  const walking = currentAction === "walk";
  const flying = currentAction === "fly";
  const jumping = currentAction === "jump";
  const waving = currentAction === "wave";
  const looking = currentAction === "look";

  // Automatic walking between random positions.
  if (walking) {
    doraemon.position.x = THREE.MathUtils.lerp(startX, targetX, t);
    facing = THREE.MathUtils.lerp(startFacing, targetFacing, t);
  } else {
    facing = THREE.MathUtils.damp(facing, targetFacing, 1.5, dt);
  }

  doraemon.rotation.y = facing;

  // Walk, jump, and flight height.
  let height = 0;

  if (walking) {
    height = Math.abs(Math.sin(time * 7)) * 0.035;
  }

  if (jumping) {
    height = Math.abs(Math.sin(actionElapsed * Math.PI * 1.1)) * 0.75;
  }

  if (flying) {
    height = 1.25 + Math.sin(time * 3) * 0.14;
    doraemon.position.x = THREE.MathUtils.lerp(
      startX, targetX, smooth(actionTimer / actionDuration)
    );
    rotor.rotation.y += dt * 25;
  } else {
    rotor.rotation.y += dt * 4;
  }

  doraemon.position.y = THREE.MathUtils.damp(
    doraemon.position.y, height, 5, dt
  );

  // Limb movement.
  const stride = walking ? Math.sin(time * 7) * 0.48 : 0;

  legL.rotation.x = stride;
  legR.rotation.x = -stride;

  armL.rotation.x = -stride * 0.8;
  armR.rotation.x = stride * 0.8;

  if (waving) {
    armR.rotation.x = -2.1 + Math.sin(time * 8) * 0.32;
    armR.rotation.z = -0.3;
  } else {
    armR.rotation.z = THREE.MathUtils.damp(armR.rotation.z, 0, 5, dt);
  }

  if (flying) {
    legL.rotation.x = -0.35;
    legR.rotation.x = -0.35;
    armL.rotation.x = -0.7;
    armR.rotation.x = -0.7;
  }

  // Look around.
  body.rotation.y = looking ? Math.sin(time * 2) * 0.20 : 0;
  body.rotation.z = walking ? Math.sin(time * 7) * 0.02 : 0;

  // Floating ground shadow.
  shadow.position.x = doraemon.position.x;
  shadow.material.opacity = 0.34 - height * 0.12;
  shadow.scale.setScalar(1 + height * 0.15);

  // Anywhere Door opens and closes.
  if (currentAction === "door") {
    portal.scale.setScalar(Math.min(actionElapsed / 0.7, 1));
    portal.rotation.y = Math.sin(time) * 0.07;
    portalGlass.material.opacity = 0.35 + Math.sin(time * 4) * 0.18;

    doorL.position.x = THREE.MathUtils.damp(
      doorL.position.x, -0.29, 3, dt
    );
    doorR.position.x = THREE.MathUtils.damp(
      doorR.position.x, 0.29, 3, dt
    );
  }

  // Magic particles swirl around Doraemon.
  if (currentAction === "magic") {
    magic.position.set(doraemon.position.x, 1.8 + height, 0.3);

    for (const p of particles) {
      p.angle += dt * p.speed;
      p.mesh.position.set(
        Math.cos(p.angle) * p.radius,
        Math.sin(p.angle * 1.5) * 0.3 + p.height,
        Math.sin(p.angle) * p.radius
      );
    }
  }

  ring.rotation.z += dt * 0.12;
  glow.intensity = 26 + Math.sin(time * 2) * 4;

  controls.update();
  renderer.render(scene, camera);
}

animate();

// =====================================
// 11. RESIZE
// =====================================
window.addEventListener("resize", () => {
  const w = container.clientWidth;
  const h = container.clientHeight;

  if (!w || !h) return;

  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
});

document.getElementById("loading")?.remove();
