const $=id=>document.getElementById(id);
async function api(path,options={}){const r=await fetch(path,{headers:{'Content-Type':'application/json'},...options});const data=await r.json().catch(()=>({detail:'Request failed'}));if(!r.ok)throw new Error(data.detail||'Request failed');return data}
function payload(form){return Object.fromEntries(new FormData(form).entries())}
function showView(id){document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));$(id).classList.add('active')}
function escapeHtml(value){return String(value==null?'':value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
document.querySelectorAll('[data-view]').forEach(btn=>btn.onclick=()=>{showView(btn.dataset.view);if(btn.dataset.view==='owner')loadDashboard();if(btn.dataset.view==='customer')loadCustomerDashboard()});
async function loadServices(){const services=await api('/api/public/services');$('serviceSelect').innerHTML=services.length?services.map(s=>`<option value="${s.id}">${escapeHtml(s.name)} · $${Number(s.price).toFixed(2)}</option>`).join(''):'<option value="">No services available</option>'}
$('bookingForm').onsubmit=async e=>{e.preventDefault();try{const item=await api('/api/public/bookings',{method:'POST',body:JSON.stringify({service_id:Number($('serviceSelect').value),appointment_at:$('appointmentAt').value,customer_name:$('customerName').value,customer_email:$('customerEmail').value})});$('bookingMessage').textContent=`Booking #${item.id} confirmed.`;e.target.reset()}catch(err){$('bookingMessage').textContent=err.message;$('bookingMessage').className='message error'}};

function ownerShowGate(){$('ownerHeading').hidden=false;$('authPanel').hidden=false;$('forgotPasswordForm').hidden=true;$('dashboard').hidden=true}
function ownerShowDashboard(){$('ownerHeading').hidden=true;$('authPanel').hidden=true;$('forgotPasswordForm').hidden=true;$('dashboard').hidden=false}
async function auth(form,path){try{await api(path,{method:'POST',body:JSON.stringify(payload(form))});await loadDashboard()}catch(err){$('ownerMessage').textContent=err.message;$('ownerMessage').className='message error'}}
$('registerForm').onsubmit=e=>{e.preventDefault();auth(e.target,'/api/auth/register')};
$('loginForm').onsubmit=e=>{e.preventDefault();auth(e.target,'/api/auth/login')};
$('logoutBtn').onclick=async()=>{await api('/api/auth/logout',{method:'POST'});ownerShowGate()};
$('profileForm').onsubmit=async e=>{e.preventDefault();await api('/api/owner/profile',{method:'PUT',body:JSON.stringify({business_name:$('businessName').value})});await loadDashboard()};
$('serviceForm').onsubmit=async e=>{e.preventDefault();await api('/api/owner/services',{method:'POST',body:JSON.stringify({name:$('serviceName').value,duration_minutes:Number($('serviceDuration').value),price:Number($('servicePrice').value)})});e.target.reset();await loadDashboard();await loadServices()};
async function updateBooking(id,status){await api(`/api/owner/bookings/${id}`,{method:'PATCH',body:JSON.stringify({status})});await loadDashboard()}
async function loadDashboard(){
  try{
    const d=await api('/api/owner/dashboard');
    ownerShowDashboard();
    $('businessName').value=d.profile.business_name||'';
    $('businessTitle').textContent=d.profile.business_name||'Your business';
    $('bookingList').innerHTML=d.bookings.length?d.bookings.map(b=>`<div class="booking"><div><strong>${escapeHtml(b.customer_name)}</strong><br>${escapeHtml(b.service_name)} · ${new Date(b.appointment_at).toLocaleString()}<br><small>${escapeHtml(b.customer_email)} · ${escapeHtml(b.status)}</small></div><select onchange="updateBooking(${b.id},this.value)"><option ${b.status==='confirmed'?'selected':''}>confirmed</option><option ${b.status==='completed'?'selected':''}>completed</option><option ${b.status==='cancelled'?'selected':''}>cancelled</option></select></div>`).join(''):'<p>No bookings yet.</p>';
    $('serviceList').innerHTML=d.services.length?d.services.map(s=>`<div class="service-row"><div><strong>${escapeHtml(s.name)}</strong><br><small>${s.duration_minutes} min · $${Number(s.price).toFixed(2)}</small></div></div>`).join(''):'<p>No services yet. Add your first one above.</p>';
    $('statBookings').textContent=d.bookings.length;
    $('statServices').textContent=d.services.length;
    const now=new Date();
    $('statUpcoming').textContent=d.bookings.filter(b=>b.status==='confirmed'&&new Date(b.appointment_at)>now).length;
    await loadEmailSettings();
  }catch(_){
    ownerShowGate();
  }
}
document.querySelectorAll('.sidebar-link[data-owner-panel]').forEach(btn=>btn.onclick=()=>{
  document.querySelectorAll('.sidebar-link[data-owner-panel]').forEach(b=>b.classList.remove('active'));
  document.querySelectorAll('.owner-panel').forEach(p=>p.classList.remove('active'));
  btn.classList.add('active');
  document.querySelector(`.owner-panel[data-owner-panel-content="${btn.dataset.ownerPanel}"]`).classList.add('active');
});
async function loadEmailSettings(){try{const s=await api('/api/owner/email-settings');$('emailProviderSelect').value=s.provider;$('gmailFields').hidden=s.provider!=='gmail';$('gmailAddress').value=s.gmail_address||'';$('gmailAppPassword').type='password';$('gmailAppPassword').value='';$('gmailAppPassword').placeholder=s.gmail_app_password_configured?'•••••••• (saved — leave blank to keep)':'Leave blank to keep current';$('unmaskGmailPasswordBtn').textContent='Show'}catch(_){}}
$('emailProviderSelect').onchange=()=>{$('gmailFields').hidden=$('emailProviderSelect').value!=='gmail'};
$('emailSettingsForm').onsubmit=async e=>{e.preventDefault();try{const body={provider:$('emailProviderSelect').value,gmail_address:$('gmailAddress').value||null};if($('gmailAppPassword').value)body.gmail_app_password=$('gmailAppPassword').value;await api('/api/owner/email-settings',{method:'PUT',body:JSON.stringify(body)});$('emailSettingsMessage').textContent='Saved.';$('emailSettingsMessage').className='message';await loadEmailSettings()}catch(err){$('emailSettingsMessage').textContent=err.message;$('emailSettingsMessage').className='message error'}};
$('unmaskGmailPasswordBtn').onclick=async()=>{const field=$('gmailAppPassword');const btn=$('unmaskGmailPasswordBtn');if(field.type==='text'){field.type='password';field.value='';field.placeholder='Leave blank to keep current';btn.textContent='Show';return}try{const data=await api('/api/owner/email-settings/reveal',{method:'POST'});field.type='text';field.value=data.gmail_app_password;btn.textContent='Hide'}catch(err){$('emailSettingsMessage').textContent=err.message;$('emailSettingsMessage').className='message error'}};
$('ownerForgotLink').onclick=()=>{$('ownerHeading').hidden=true;$('authPanel').hidden=true;$('forgotPasswordForm').hidden=false};
$('backToSigninLink').onclick=()=>{$('forgotPasswordForm').hidden=true;$('ownerHeading').hidden=false;$('authPanel').hidden=false};
$('forgotPasswordForm').onsubmit=async e=>{e.preventDefault();try{const data=await api('/api/auth/forgot-password',{method:'POST',body:JSON.stringify({email:$('forgotEmail').value})});$('ownerMessage').textContent=data.message;$('ownerMessage').className='message'}catch(err){$('ownerMessage').textContent=err.message;$('ownerMessage').className='message error'}};

async function customerAuth(form,path){try{await api(path,{method:'POST',body:JSON.stringify(payload(form))});await loadCustomerDashboard()}catch(err){$('customerMessage').textContent=err.message;$('customerMessage').className='message error'}}
$('customerRegisterForm').onsubmit=e=>{e.preventDefault();customerAuth(e.target,'/api/customer/auth/register')};
$('customerLoginForm').onsubmit=e=>{e.preventDefault();customerAuth(e.target,'/api/customer/auth/login')};
$('customerLogoutBtn').onclick=async()=>{await api('/api/customer/auth/logout',{method:'POST'});$('customerDashboard').hidden=true;$('customerAuthPanel').hidden=false};
$('customerForgotLink').onclick=()=>{$('customerAuthPanel').hidden=true;$('customerForgotForm').hidden=false};
$('customerBackToSigninLink').onclick=()=>{$('customerForgotForm').hidden=true;$('customerAuthPanel').hidden=false};
$('customerForgotForm').onsubmit=async e=>{e.preventDefault();try{const data=await api('/api/customer/auth/forgot-password',{method:'POST',body:JSON.stringify({email:$('customerForgotEmail').value})});$('customerMessage').textContent=data.message;$('customerMessage').className='message'}catch(err){$('customerMessage').textContent=err.message;$('customerMessage').className='message error'}};
async function loadCustomerDashboard(){try{const bookings=await api('/api/customer/bookings');$('customerAuthPanel').hidden=true;$('customerForgotForm').hidden=true;$('customerDashboard').hidden=false;$('customerBookingList').innerHTML=bookings.length?bookings.map(b=>`<div class="booking"><div><strong>${escapeHtml(b.service_name)}</strong><br>${new Date(b.appointment_at).toLocaleString()}<br><small>${escapeHtml(b.status)}</small></div></div>`).join(''):'<p>No bookings yet.</p>'}catch(_){$('customerAuthPanel').hidden=false;$('customerDashboard').hidden=true}}

const resetParams=new URLSearchParams(location.search);
const resetToken=resetParams.get('token');
const resetType=resetParams.get('type')==='customer'?'customer':'owner';
if(resetToken){
  showView('resetPassword');
  $('resetPasswordForm').onsubmit=async e=>{e.preventDefault();try{const path=resetType==='customer'?'/api/customer/auth/reset-password':'/api/auth/reset-password';const data=await api(path,{method:'POST',body:JSON.stringify({token:resetToken,new_password:$('newPassword').value})});$('resetMessage').textContent=data.message}catch(err){$('resetMessage').textContent=err.message;$('resetMessage').className='message error'}};
}
loadServices();
