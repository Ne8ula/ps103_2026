import * as THREE from 'three';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js';

// Original visualization geometry, deliberately not a manufacturing mesh or print profile.
export function makeLayerMaterial() {
  const material = new THREE.MeshPhysicalMaterial({color:'#739e83',roughness:.31,metalness:.08,clearcoat:.45,clearcoatRoughness:.38,iridescence:.18,iridescenceIOR:1.22,envMapIntensity:.45});
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
  material.customProgramCacheKey = () => 'benchmate-satin-layer-v1';
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
  const dark=new THREE.MeshStandardMaterial({color:'#3b554b',roughness:.7});
  const inner=new THREE.MeshPhysicalMaterial({color:'#96b89f',roughness:.55,clearcoat:.15});
  const profile=new THREE.CatmullRomCurve3([[0,.08],[.32,.07],[.52,.12],[.60,.28],[.60,.48],[.56,.72],[.47,1.02],[.38,1.32],[.36,1.52],[.0,1.61]].map(([x,y])=>new THREE.Vector3(x,y,0))).getPoints(64).map(p=>new THREE.Vector2(Math.max(0,p.x),p.y));
  piece(cat,new THREE.LatheGeometry(profile,64),satin,[0,0,0],[1,1,.8]);
  piece(cat,sphere,satin,[0,1.82,.025],[.70,.59,.53]);
  for(const side of [-1,1]) {
    const earProfile=[[0,0],[.20,0],[.24,.08],[.20,.22],[.13,.38],[.045,.50],[0,.53]].map(p=>new THREE.Vector2(...p));
    const ear=piece(cat,new THREE.LatheGeometry(earProfile,40),satin,[side*.45,2.07,-.02],[1,1,.60]);ear.rotation.z=-side*.18;
    const inset=piece(cat,sphere,inner,[side*.505,2.35,.126],[.075,.14,.025]);inset.rotation.z=-side*.20;
    piece(cat,sphere,satin,[side*.26,.16,.36],[.24,.15,.30]);
    piece(cat,sphere,satin,[side*.25,.60,.35],[.14,.48,.16]);
    piece(cat,sphere,dark,[side*.235,1.87,.519],[.025,.044,.016]);
  }
  piece(cat,sphere,dark,[0,1.74,.554],[.046,.027,.017]);
  tube(cat,[[0,1.72,.554],[0,1.67,.547],[-.065,1.64,.531],[-.115,1.67,.520]],.009,dark,16);
  tube(cat,[[0,1.67,.547],[.065,1.64,.531],[.115,1.67,.520]],.009,dark,12);
  tube(cat,[[.47,.22,-.12],[.88,.25,-.02],[1.08,.56,.015],[1.12,.91,.01],[1.02,1.08,.055]],.13,satin);
  piece(cat,sphere,satin,[1.02,1.08,.055],[.13,.13,.13]);
  cat.userData.visualOnly=true;
  return cat;
}

function createPlate(type,lifting) {
  const group=new THREE.Group();
  const gold=new THREE.MeshStandardMaterial({color:'#b6a271',roughness:.88,metalness:.12});
  const steel=new THREE.MeshStandardMaterial({color:'#77807a',roughness:.5,metalness:.7});
  piece(group,new RoundedBoxGeometry(2.8,.075,2.55,3,.065),steel,[0,.1,0]);
  piece(group,new RoundedBoxGeometry(2.78,.026,2.53,3,.035),gold,[0,.15,0]);
  const edge=new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(2.64,.01,2.4)),new THREE.LineBasicMaterial({color:'#e5d8b2',transparent:true,opacity:.55}));edge.position.y=.172;group.add(edge);
  if(type==='layer') {
    const filament=new THREE.MeshStandardMaterial({color:lifting?'#ca8a3f':'#a6cda4',roughness:.56});
    const points=[];
    for(let i=0;i<20;i++) {const z=-.58+i*.06;const width=.65*Math.sqrt(1-(z/.78)**2);points.push([-width,.198,z],[width,.198,z]);if(i<19)points.push([width,.198,z+.03]);}
    // A deliberately schematic joined line example, not a sliced cat toolpath.
    const snake=[];for(let i=0;i<20;i++){const z=-.58+i*.06,w=.68*Math.sqrt(1-(z/.83)**2);snake.push([i%2?-w:w,.198,z],[i%2?w:-w,.198,z]);}
    if(lifting){snake[snake.length-1][1]=.43;snake[snake.length-2][1]=.32;}
    tube(group,snake,.018,filament,160);
  }
  if(type==='clean') {
    const bottle=new THREE.MeshPhysicalMaterial({color:'#c0d0a9',roughness:.56});
    piece(group,new RoundedBoxGeometry(.40,.72,.32,4,.10),bottle,[-.9,.57,-.74]);
    piece(group,new THREE.CylinderGeometry(.10,.10,.16,24),new THREE.MeshStandardMaterial({color:'#314b38'}),[-.9,1.01,-.74]);
    piece(group,new RoundedBoxGeometry(.6,.16,.40,3,.07),new THREE.MeshStandardMaterial({color:'#e6ca7f',roughness:1}),[.83,.26,-.56]);
  }
  if(type==='release') {const cat=createCat();cat.scale.setScalar(.62);cat.position.y=.18;group.add(cat);}
  return group;
}

function createEquipment(type) {
  const group=new THREE.Group();
  const pale=new THREE.MeshPhysicalMaterial({color:'#dce4d6',roughness:.45,clearcoat:.2});
  const dark=new THREE.MeshStandardMaterial({color:'#46504a',roughness:.55,metalness:.25});
  if(type==='spool') {
    const filament=piece(group,new THREE.CylinderGeometry(.7,.7,.60,64),makeLayerMaterial(),[0,1,0]);filament.rotation.x=Math.PI/2;
    for(const z of [-.34,.34]) {const flange=piece(group,new THREE.CylinderGeometry(.92,.92,.07,64),pale,[0,1,z]);flange.rotation.x=Math.PI/2;const hub=piece(group,new THREE.TorusGeometry(.20,.045,16,48),dark,[0,1,z+(z>0?.055:-.055)]);}
    const label=piece(group,new THREE.CylinderGeometry(.35,.35,.015,48),new THREE.MeshStandardMaterial({color:'#a9bd84',roughness:.7}),[0,1,.392]);label.rotation.x=Math.PI/2;
    const hole=piece(group,new THREE.CylinderGeometry(.14,.14,.025,40),dark,[0,1,.41]);hole.rotation.x=Math.PI/2;
    piece(group,new RoundedBoxGeometry(.95,.15,.8,3,.08),dark,[0,.13,0]);
  }else{
    piece(group,new RoundedBoxGeometry(1.9,.28,1.65,3,.07),dark,[0,.20,0]);
    piece(group,new RoundedBoxGeometry(1.9,.22,1.65,3,.05),pale,[0,2.40,0]);
    for(const x of [-.85,.85])for(const z of [-.70,.70])piece(group,new RoundedBoxGeometry(.12,2.05,.13,2,.025),pale,[x,1.3,z]);
    const glass=new THREE.MeshPhysicalMaterial({color:'#c3d9d3',transparent:true,opacity:.22,roughness:.4,metalness:.1,side:THREE.DoubleSide,depthWrite:false});
    piece(group,new THREE.PlaneGeometry(1.72,2),glass,[0,1.3,-.74]);const side=piece(group,new THREE.PlaneGeometry(1.45,2),glass,[.86,1.3,0]);side.rotation.y=Math.PI/2;
    piece(group,new RoundedBoxGeometry(1.52,.07,1.34,2,.04),new THREE.MeshStandardMaterial({color:'#b4a16e',roughness:.8}),[0,.50,0]);
    const cat=createCat();cat.scale.setScalar(.45);cat.position.y=.55;group.add(cat);
    piece(group,new RoundedBoxGeometry(.45,.25,.08,2,.02),dark,[-.48,2.39,.85]);
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
    const key=new THREE.DirectionalLight('#fff7e5',2.4);key.position.set(-3,7,5);key.castShadow=true;key.shadow.mapSize.set(1024,1024);key.shadow.camera.left=-3;key.shadow.camera.right=3;key.shadow.camera.top=4;key.shadow.camera.bottom=-3;key.shadow.normalBias=.025;key.shadow.bias=-.0002;key.shadow.radius=5;scene.add(key);
    const rim=new THREE.DirectionalLight('#e2f6f1',1.6);rim.position.set(3,3,-3);scene.add(rim);scene.add(new THREE.HemisphereLight('#f8fffa','#8d9e8d',.7));
    model=isPlate?createPlate(type==='studio'?'release':type,lifting):['spool','printer'].includes(type)?createEquipment(type):createCat();scene.add(model);
    const floor=new THREE.Mesh(new THREE.PlaneGeometry(200,200),new THREE.ShadowMaterial({opacity:.055}));floor.rotation.x=-Math.PI/2;floor.position.y=-.008;floor.receiveShadow=true;scene.add(floor);
    const contact=new THREE.Mesh(new THREE.PlaneGeometry(2.4,1.8),new THREE.ShaderMaterial({transparent:true,depthWrite:false,vertexShader:'varying vec2 vUv; void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',fragmentShader:'varying vec2 vUv; void main(){vec2 p=(vUv-0.5)*2.0;float a=exp(-dot(p,p)*4.5)*0.22;gl_FragColor=vec4(0.24,0.32,0.24,a);}'}));contact.rotation.x=-Math.PI/2;contact.position.set(.1,.001,0);scene.add(contact);
    function render() {
      if(disposed)return;const width=host.clientWidth,height=host.clientHeight;if(!width||!height)return;
      renderer.setSize(width,height,false);camera.aspect=width/height;
      if(isPlate){camera.position.set(currentView===1?0:3.1,currentView===2?6:3.9,currentView===1?5.3:4.8);camera.lookAt(0,.28,0);camera.fov=currentView===2?27:32;}
      else {camera.position.set(currentView===1?0:currentView===2?2.5:2.8,2.4,currentView===1?6.8:5.7);camera.lookAt(.12,currentView===2?1.85:1.31,0);camera.fov=currentView===2?22:28;}
      camera.updateProjectionMatrix();renderer.render(scene,camera);
    }
    const contextLost=event=>{event.preventDefault();onError?.('3D unavailable — showing the original illustration.');};
    renderer.domElement.addEventListener('webglcontextlost',contextLost);
    observer=new ResizeObserver(render);observer.observe(host);render();onReady?.();
    return {setView(value){currentView=value;render();},dispose(){disposed=true;observer.disconnect();renderer.domElement.removeEventListener('webglcontextlost',contextLost);disposeScene(scene);environment.dispose();pmrem.dispose();renderer.dispose();renderer.domElement.remove();}};
  } catch(error) {observer?.disconnect();if(scene)disposeScene(scene);environment?.dispose();pmrem?.dispose();renderer?.dispose();renderer?.domElement.remove();onError?.('3D unavailable — showing the original illustration.');return {setView(){},dispose(){disposed=true;}};}
}
function disposeScene(scene) {
  const materials=new Set(),geometries=new Set();scene.traverse(obj=>{if(obj.geometry&&obj.geometry!==sphere)geometries.add(obj.geometry);if(obj.material)(Array.isArray(obj.material)?obj.material:[obj.material]).forEach(m=>materials.add(m));});
  geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());
}
