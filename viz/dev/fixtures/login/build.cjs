// Golden "login" fixture builder (dev-only). Renders login.viz.html from map.d2 + the inline VIZ
// below, using the REAL viz/template.html. Resolves paths from __dirname (not a hard-coded HOME)
// and mirrors build-viz.cjs's safe injection. Run: `node build.cjs` (needs the d2 binary).
const fs=require('fs'), path=require('path'), os=require('os'), {execFileSync}=require('child_process');
const VIZ_DIR=path.resolve(__dirname,'../../..');          // viz/dev/fixtures/login -> viz/
const tmpl=fs.readFileSync(path.join(VIZ_DIR,'template.html'),'utf8');
function resolveD2(){for(const c of ['d2',path.join(os.homedir(),'.local/bin/d2'),'/opt/homebrew/bin/d2','/usr/local/bin/d2']){try{execFileSync(c,['--version'],{stdio:'ignore'});return c;}catch(_){}}throw new Error('d2 not found on PATH or ~/.local/bin');}
function compileD2(d2bin,src){const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'viz-fx-'));const inF=path.join(tmp,'m.d2'),outF=path.join(tmp,'m.svg');fs.writeFileSync(inF,src);execFileSync(d2bin,['--theme','0','--pad','24',inF,outF],{stdio:'pipe'});const svg=fs.readFileSync(outF,'utf8');fs.rmSync(tmp,{recursive:true,force:true});return svg;}
const mapSVG=compileD2(resolveD2(),fs.readFileSync(path.join(__dirname,'map.d2'),'utf8'));
const VIZ={
  title:"Login", scope:"what just changed",
  breadcrumb:["Whole app","Login feature"],
  footer:"Drawn from LoginForm.tsx, auth.ts · commit a1b2c3d · valid as of 2026-06-01",
  legend:true, mapSVG,
  mapNodes:[
    {key:"screen",label:"Login screen",role:"ui",sub:"LoginForm.tsx",explain:"The page with the email and password boxes and the Sign in button. The only part of all this you actually look at."},
    {key:"auth",label:"Auth logic",role:"logic",sub:"auth.ts",here:true,explain:"The decision-maker. It takes what you typed, checks it with the server, and decides whether you're allowed in. This is the piece being changed."},
    {key:"loginApi",label:"Login API",role:"outside",sub:"POST /login",explain:"A service on the internet, outside your app, that confirms your password is correct and hands back a token."},
    {key:"store",label:"Token store",role:"store",sub:"localStorage",explain:"A small safe spot in your browser that keeps the token, so you don't have to log in again on every page."}
  ],
  flow:[{role:"ui",label:"email + password"},{arrow:"check it's filled in"},{role:"logic",label:"validate"},{arrow:"send securely"},{role:"outside",label:"POST /login"},{arrow:"server replies"},{role:"store",label:"token"},{arrow:"remember you"},{role:"ui",label:"go to dashboard"}],
  shape:[{lbl:"What you type",code:"{ email, password }",role:"ui"},{t:"scramble the password, package it"},{lbl:"What is sent to the server",code:"{ email, passwordHash }",role:"outside"},{t:"server answers"},{lbl:"What comes back",code:"{ token, userId, expiresAt }",role:"outside"},{t:"keep only what's needed"},{lbl:"What is stored",code:"{ token }",role:"store"}],
  steps:[{who:"You",what:"type your email and password, click Sign in"},{who:"Login screen",what:"hands them to the Auth logic"},{who:"Auth logic",what:"asks the Login API to check them"},{who:"Login API",what:'replies "looks good, here\'s a token"'},{who:"Auth logic",what:"saves the token so you stay logged in"},{who:"Auth logic",what:"sends you to your dashboard"}],
  narr:{
    map:"This is the <b>Login</b> feature as four connected pieces. You start at the <b>Login screen</b> (blue, the part you see). It hands your email and password to the <b>Auth logic</b> (green, the part that decides) — the piece being changed right now. Auth talks to the <b>Login API</b> out in the world (amber), and saves a <b>token</b> (violet) so you stay signed in.",
    flow:"Follow your data on its journey. You type an <b>email and password</b>. They get checked, scrambled for safety, and sent to the server. The server replies with a <b>token</b> — a little pass that proves it's you — which gets remembered so the next screen knows you're logged in.",
    shape:"Watch how your data changes shape at each step. It starts as what you type, gets repackaged with the password hidden, comes back with extra details, and ends as just the one thing worth keeping: the <b>token</b>.",
    steps:"The same story, told in order. Six steps from clicking <b>Sign in</b> to landing on your dashboard. Each line is one hand-off between pieces."
  },
  status:"ok"
};
// Same safe injection as build-viz.cjs: escape "<" so a "</script>" in any string can't break out,
// and use a function replacer so "$" sequences in the JSON aren't treated as replace specials.
const dataTag='<script>window.VIZ='+JSON.stringify(VIZ).replace(/</g,'\\u003c')+';<\/script>';
const out=tmpl.replace('<!--VIZ_CONTENT-->',()=>dataTag);
fs.writeFileSync(path.join(__dirname,'login.viz.html'),out);
console.log('wrote login.viz.html',out.length,'bytes');
