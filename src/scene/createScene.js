import * as THREE from 'three';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js';

// Original visualization geometry, deliberately not a manufacturing mesh or print profile.
export function makeLayerMaterial() {
  const material = new THREE.MeshPhysicalMaterial({color:'#d7c4e7',roughness:.48,metalness:.025,clearcoat:.28,clearcoatRoughness:.5,iridescence:.12,iridescenceIOR:1.22,envMapIntensity:.38});
  material.onBeforeCompile = shader => {
    shader.vertexShader = 'varying vec3 vBenchPosition;\n' + shader.vertexShader;
    shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nvBenchPosition = (modelMatrix * vec4(position, 1.0)).xyz;');
    shader.fragmentShader = 'varying vec3 vBenchPosition;\n' + shader.fragmentShader;
    shader.fragmentShader = shader.fragmentShader.replace('#include <color_fragment>', `#include <color_fragment>
      float phase = vBenchPosition.y * 260.0;
      float ridge = sin(phase) * (1.0 - smoothstep(0.7, 3.0, fwidth(phase)));
      float grain = fract(sin(dot(floor(vBenchPosition * 720.0), vec3(12.9898,78.233,37.719))) * 43758.5453);
      diffuseColor.rgb *= 0.985 + ridge * 0.023 + (grain - 0.5) * 0.014;
    `);
  };
  material.customProgramCacheKey = () => 'benchmate-pearl-layer-v2';
  return material;
}

const sphere = new THREE.SphereGeometry(1,48,32);
function piece(group, geometry, material, position=[0,0,0], scale=[1,1,1]) {
  const object = new THREE.Mesh(geometry,material);object.position.set(...position);object.scale.set(...scale);
  object.castShadow=true;object.receiveShadow=true;group.add(object);return object;
}
function tube(group, points, radius, material, segments=48) {
  return piece(group,new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p))),segments,radius,12,false),material);
}
export function createCat() {
  const cat=new THREE.Group();cat.name='Benchmate original little cat';
  const satin=makeLayerMaterial();
  const dark=new THREE.MeshStandardMaterial({color:'#766083',roughness:.7});
  const inner=new THREE.MeshPhysicalMaterial({color:'#b39bc5',roughness:.65,clearcoat:.12});
  const profile=new THREE.CatmullRomCurve3([[0,.08],[.32,.07],[.52,.12],[.60,.28],[.60,.48],[.56,.72],[.47,1.02],[.38,1.32],[.36,1.52],[.0,1.61]].map(([x,y])=>new THREE.Vector3(x,y,0))).getPoints(64).map(p=>new THREE.Vector2(Math.max(0,p.x),p.y));
  piece(cat,new THREE.LatheGeometry(profile,64),satin,[0,0,0],[1,1,.8]);
  piece(cat,sphere,satin,[0,1.82,.025],[.70,.59,.53]);
  for(const side of [-1,1]) {
    const earProfile=[[0,0],[.20,0],[.24,.08],[.20,.22],[.13,.38],[.045,.50],[0,.53]].map(p=>new THREE.Vector2(...p));
    const ear=piece(cat,new THREE.LatheGeometry(earProfile,40),satin,[side*.45,2.07,-.02],[1,1,.60]);ear.rotation.z=-side*.18;
    const inset=piece(cat,sphere,inner,[side*.505,2.35,.126],[.075,.14,.025]);inset.rotation.z=-side*.20;
    piece(cat,sphere,satin,[side*.26,.16,.36],[.24,.15,.30]);
    piece(cat,sphere,satin,[side*.25,.60,.35],[.14,.48,.16]);
    tube(cat,[[side*.12,1.84,.552],[side*.23,1.885,.531],[side*.34,1.84,.495]],.013,dark,20);
  }
  piece(cat,sphere,inner,[0,1.74,.566],[.046,.027,.02]);
  tube(cat,[[0,1.72,.554],[0,1.67,.547],[-.065,1.64,.531],[-.115,1.67,.520]],.009,dark,16);
  tube(cat,[[0,1.67,.547],[.065,1.64,.531],[.115,1.67,.520]],.009,dark,12);
  tube(cat,[[.47,.22,-.12],[.88,.25,-.02],[1.08,.56,.015],[1.12,.91,.01],[1.02,1.08,.055]],.13,satin);
  piece(cat,sphere,satin,[1.02,1.08,.055],[.13,.13,.13]);
  cat.userData.visualOnly=true;
  return cat;
}

function createPlate(type,lifting) {
  const group=new THREE.Group();
  const gold=new THREE.MeshStandardMaterial({color:'#a08243',roughness:.83,metalness:.28});
  gold.onBeforeCompile=shader=>{
    shader.vertexShader='varying vec3 platePosition;\n'+shader.vertexShader;
    shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nplatePosition=position;');
    shader.fragmentShader='varying vec3 platePosition;\n'+shader.fragmentShader;
    shader.fragmentShader=shader.fragmentShader.replace('#include <color_fragment>',`#include <color_fragment>
      float grain=fract(sin(dot(floor(platePosition.xz*330.0),vec2(12.9898,78.233)))*43758.5453);
      diffuseColor.rgb *= .84 + grain*.32;
    `);
  };
  const steel=new THREE.MeshStandardMaterial({color:'#77807a',roughness:.5,metalness:.7});
  // Seated on a magnetic platform, with rear stops; no floating placement instruction.
  const platform=new THREE.MeshStandardMaterial({color:'#35313f',roughness:.7,metalness:.2});
  piece(group,new RoundedBoxGeometry(2.96,.14,2.72,3,.05),platform,[0,.005,0]);
  for(const x of [-1.19,1.19])piece(group,new RoundedBoxGeometry(.14,.19,.12,2,.02),platform,[x,.15,-1.29]);
  piece(group,new RoundedBoxGeometry(2.8,.075,2.55,3,.065),steel,[0,.1,0]);
  piece(group,new RoundedBoxGeometry(2.78,.026,2.53,3,.035),gold,[0,.15,0]);
  const edge=new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(2.64,.01,2.4)),new THREE.LineBasicMaterial({color:'#e5d8b2',transparent:true,opacity:.55}));edge.position.y=.172;group.add(edge);
  if(type==='layer') {
    const filament=new THREE.MeshStandardMaterial({color:'#e0d2ec',roughness:.56});
    const points=[];
    for(let i=0;i<20;i++) {const z=-.58+i*.06;const width=.65*Math.sqrt(1-(z/.78)**2);points.push([-width,.198,z],[width,.198,z]);if(i<19)points.push([width,.198,z+.03]);}
    // A deliberately schematic joined line example, not a sliced cat toolpath.
    const snake=[];for(let i=0;i<20;i++){const z=-.58+i*.06,w=.68*Math.sqrt(1-(z/.83)**2);snake.push([i%2?-w:w,.198,z],[i%2?w:-w,.198,z]);}
    if(lifting){snake[snake.length-1][1]=.43;snake[snake.length-2][1]=.32;}
    tube(group,snake,.018,filament,160);
  }
  if(type==='clean') {
    const bottle=new THREE.MeshPhysicalMaterial({color:'#d6cce1',roughness:.56});
    piece(group,new RoundedBoxGeometry(.40,.72,.32,4,.10),bottle,[-.9,.57,-.74]);
    piece(group,new THREE.CylinderGeometry(.10,.10,.16,24),new THREE.MeshStandardMaterial({color:'#314b38'}),[-.9,1.01,-.74]);
    piece(group,new RoundedBoxGeometry(.6,.16,.40,3,.07),new THREE.MeshStandardMaterial({color:'#e6ca7f',roughness:1}),[.83,.26,-.56]);
  }
  if(type==='release') {const cat=createCat();cat.scale.setScalar(.62);cat.position.y=.18;group.add(cat);}
  return group;
}

function createEquipment(type,showCat=false) {
  const group=new THREE.Group();
  const pale=new THREE.MeshPhysicalMaterial({color:'#65606d',roughness:.5,clearcoat:.18});
  const dark=new THREE.MeshStandardMaterial({color:'#302d37',roughness:.55,metalness:.25});
  if(type==='spool') {
    const filament=piece(group,new THREE.CylinderGeometry(.7,.7,.60,64),makeLayerMaterial(),[0,1,0]);filament.rotation.x=Math.PI/2;
    for(const z of [-.34,.34]) {
      piece(group,new THREE.TorusGeometry(.84,.075,16,64),dark,[0,1,z]);
      piece(group,new THREE.TorusGeometry(.24,.06,16,48),dark,[0,1,z]);
      for(let i=0;i<6;i++){const angle=i*Math.PI/3;const spoke=piece(group,new RoundedBoxGeometry(.10,.63,.055,2,.025),dark,[Math.sin(angle)*.52,1+Math.cos(angle)*.52,z]);spoke.rotation.z=-angle;}
    }
    const label=piece(group,new THREE.CylinderGeometry(.35,.35,.015,48),new THREE.MeshStandardMaterial({color:'#ccde72',roughness:.7}),[0,1,.392]);label.rotation.x=Math.PI/2;
    const hole=piece(group,new THREE.CylinderGeometry(.14,.14,.025,40),dark,[0,1,.41]);hole.rotation.x=Math.PI/2;
    piece(group,new RoundedBoxGeometry(.95,.15,.8,3,.08),dark,[0,.13,0]);
  }else{
    piece(group,new RoundedBoxGeometry(1.9,.28,1.65,3,.07),dark,[0,.20,0]);
    piece(group,new RoundedBoxGeometry(1.9,.22,1.65,3,.05),pale,[0,2.40,0]);
    for(const x of [-.85,.85])for(const z of [-.70,.70])piece(group,new RoundedBoxGeometry(.12,2.05,.13,2,.025),pale,[x,1.3,z]);
    piece(group,new RoundedBoxGeometry(1.65,1.98,.065,2,.02),dark,[0,1.35,-.74]);
    piece(group,new RoundedBoxGeometry(.08,1.99,1.38,2,.02),pale,[-.89,1.35,0]);
    piece(group,new RoundedBoxGeometry(1.65,.3,.14,2,.025),pale,[0,2.22,.72]);
    const rail=new THREE.MeshStandardMaterial({color:'#a6a1ac',metalness:.75,roughness:.35});
    for(const x of [-.69,.69])piece(group,new THREE.CylinderGeometry(.025,.025,1.65,16),rail,[x,1.35,-.45]);
    piece(group,new THREE.BoxGeometry(1.42,.065,.07),rail,[0,1.88,.05]);
    piece(group,new RoundedBoxGeometry(.36,.3,.33,2,.03),dark,[.1,1.76,.08]);
    piece(group,new THREE.ConeGeometry(.055,.12,16),rail,[.1,1.57,.08]).rotation.z=Math.PI;
    const glass=new THREE.MeshPhysicalMaterial({color:'#c3d9d3',transparent:true,opacity:.22,roughness:.4,metalness:.1,side:THREE.DoubleSide,depthWrite:false});
    piece(group,new THREE.PlaneGeometry(1.72,2),glass,[0,1.3,-.74]);const side=piece(group,new THREE.PlaneGeometry(1.45,2),glass,[.86,1.3,0]);side.rotation.y=Math.PI/2;
    piece(group,new RoundedBoxGeometry(1.52,.07,1.34,2,.04),new THREE.MeshStandardMaterial({color:'#b4a16e',roughness:.8}),[0,.50,0]);
    if(showCat){const cat=createCat();cat.scale.setScalar(.38);cat.position.y=.55;group.add(cat);}
    piece(group,new RoundedBoxGeometry(.45,.25,.08,2,.02),dark,[-.48,2.39,.85]);
    piece(group,new THREE.PlaneGeometry(.34,.16),new THREE.MeshStandardMaterial({color:'#201b2d',roughness:.3}),[-.48,2.4,.896]);
  }
  return group;
}

function createWorkshop(){
  const group=new THREE.Group();
  const printer=createEquipment('printer');printer.scale.setScalar(.85);printer.position.set(-.64,0,-.38);group.add(printer);
  const cat=createCat();cat.scale.setScalar(.73);cat.position.set(.64,0,.68);group.add(cat);
  const spool=createEquipment('spool');spool.scale.setScalar(.54);spool.position.set(1.02,0,-.43);group.add(spool);
  return group;
}
function createPreview(type){
  const group=new THREE.Group(),material=makeLayerMaterial();
  if(type==='tray'){
    const profile=[[0,.05],[.65,.05],[.9,.13],[1,.25],[1.04,.65],[1,.7],[.95,.64],[.9,.25],[.7,.15],[0,.15]].map(p=>new THREE.Vector2(...p));
    const geo=new THREE.LatheGeometry(profile,128),positions=geo.attributes.position;
    for(let i=0;i<positions.count;i++){const x=positions.getX(i),z=positions.getZ(i),a=Math.atan2(z,x),r=Math.hypot(x,z);const ripple=1+.07*Math.sin(a*12);positions.setXYZ(i,x*ripple,positions.getY(i)+.55,z*ripple);}
    geo.computeVertexNormals();piece(group,geo,material);
  }else{
    const pebble=piece(group,new THREE.TorusGeometry(.62,.25,32,80,Math.PI*1.82),material,[0,.9,0],[1,1,.8]);pebble.rotation.set(Math.PI/2,0,.35);
    tube(group,[[-1.3,.72,.3],[-.5,.72,.3],[0,.72,0],[.6,.72,-.2],[1.3,.72,-.2]],.045,new THREE.MeshStandardMaterial({color:'#3b3345',roughness:.8}));
  }
  return group;
}

export function mountProductScene(host,{type='cat',lifting=false,view=0,onReady,onError}={}) {
  let renderer,scene,environment,pmrem,observer,model;
  let disposed=false,currentView=view;
  const isPlate=['plate','layer','clean','release','studio'].includes(type);
  try {
    renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'low-power'});
    renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.75));renderer.setClearColor(0x000000,0);
    renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=.88;
    renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
    renderer.domElement.setAttribute('aria-hidden','true');host.appendChild(renderer.domElement);
    scene=new THREE.Scene();
    const studio=new RoomEnvironment();pmrem=new THREE.PMREMGenerator(renderer);environment=pmrem.fromScene(studio,.04);scene.environment=environment.texture;studio.dispose();
    const camera=new THREE.PerspectiveCamera(32,1,.1,30);
    const key=new THREE.DirectionalLight('#faf5ff',1.9);key.position.set(-3,7,5);key.castShadow=true;key.shadow.mapSize.set(1024,1024);key.shadow.camera.left=-3;key.shadow.camera.right=3;key.shadow.camera.top=4;key.shadow.camera.bottom=-3;key.shadow.normalBias=.025;key.shadow.bias=-.0002;key.shadow.radius=5;scene.add(key);
    const rim=new THREE.DirectionalLight('#d8c4f5',1.4);rim.position.set(3,3,-3);scene.add(rim);scene.add(new THREE.HemisphereLight('#faf4ff','#827089',.55));
    model=isPlate?createPlate(type==='studio'?'release':type,lifting):type==='workshop'?createWorkshop():['tray','pebble'].includes(type)?createPreview(type):['spool','printer','printing'].includes(type)?createEquipment(type==='printing'?'printer':type,type==='printing'):createCat();scene.add(model);
    const floor=new THREE.Mesh(new THREE.PlaneGeometry(200,200),new THREE.ShadowMaterial({opacity:.055}));floor.rotation.x=-Math.PI/2;floor.position.y=-.008;floor.receiveShadow=true;scene.add(floor);
    const contact=new THREE.Mesh(new THREE.PlaneGeometry(2.4,1.8),new THREE.ShaderMaterial({transparent:true,depthWrite:false,vertexShader:'varying vec2 vUv; void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',fragmentShader:'varying vec2 vUv; void main(){vec2 p=(vUv-0.5)*2.0;float a=exp(-dot(p,p)*4.5)*0.22;gl_FragColor=vec4(0.24,0.32,0.24,a);}'}));contact.rotation.x=-Math.PI/2;contact.position.set(.1,.001,0);scene.add(contact);
    function render() {
      if(disposed)return;const width=host.clientWidth,height=host.clientHeight;if(!width||!height)return;
      renderer.setSize(width,height,false);camera.aspect=width/height;
      if(type==='workshop'){camera.position.set(currentView===1?0:2.6,2.65,7.4);camera.lookAt(.05,1.1,0);camera.fov=currentView===2?25:32;}
      else if(['tray','pebble'].includes(type)){camera.position.set(2,3.6,4.3);camera.lookAt(0,.8,0);camera.fov=32;}
      else if(isPlate){camera.position.set(currentView===1?0:3.1,currentView===2?6:3.9,currentView===1?5.3:4.8);camera.lookAt(0,.28,0);camera.fov=currentView===2?27:32;}
      else {camera.position.set(currentView===1?0:currentView===2?2.5:2.8,2.4,currentView===1?6.8:5.7);camera.lookAt(.12,currentView===2?1.85:1.31,0);camera.fov=currentView===2?22:28;}
      camera.updateProjectionMatrix();renderer.render(scene,camera);
    }
    const contextLost=event=>{event.preventDefault();onError?.('3D unavailable — showing the original illustration.');};
    renderer.domElement.addEventListener('webglcontextlost',contextLost);
    observer=new ResizeObserver(render);observer.observe(host);render();onReady?.();
    return {setView(value){currentView=value;render();},dispose(){disposed=true;observer.disconnect();renderer.domElement.removeEventListener('webglcontextlost',contextLost);disposeScene(scene);environment.dispose();pmrem.dispose();renderer.dispose();renderer.forceContextLoss();renderer.domElement.remove();}};
  } catch(error) {observer?.disconnect();if(scene)disposeScene(scene);environment?.dispose();pmrem?.dispose();renderer?.dispose();renderer?.domElement.remove();onError?.('3D unavailable — showing the original illustration.');return {setView(){},dispose(){disposed=true;}};}
}
function disposeScene(scene) {
  const materials=new Set(),geometries=new Set();scene.traverse(obj=>{if(obj.geometry&&obj.geometry!==sphere)geometries.add(obj.geometry);if(obj.material)(Array.isArray(obj.material)?obj.material:[obj.material]).forEach(m=>materials.add(m));});
  geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());
}
