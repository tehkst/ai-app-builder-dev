const $=id=>document.getElementById(id);
async function api(path,options={}){const r=await fetch(path,{headers:{'Content-Type':'application/json'},...options});const data=await r.json().catch(()=>({detail:'Request failed'}));if(!r.ok)throw new Error(data.detail||'Request failed');return data}
function payload(form){return Object.fromEntries(new FormData(form).entries())}
function showView(id){document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));$(id).classList.add('active')}
document.querySelectorAll('nav button').forEach(btn=>btn.onclick=()=>{showView(btn.dataset.view);if(btn.dataset.view==='owner')loadDashboard();if(btn.dataset.view==='customer')loadCustomerDashboard()});
async function loadServices(){const services=await api('/api/public/services');$('serviceSelect').innerHTML=services.length?services.map(s=>`<option value="${s.id}">${s.name} · $${Number(s.price).toFixed(2)}</option>`).join(''):'<option value="">No services available</option>'}
$('bookingForm').onsubmit=async e=>{e.preventDefault();try{const item=await api('/api/public/bookings',{method:'POST',body:JSON.stringify({service_id:Number($('serviceSelect').value),appointment_at:$('appointmentAt').value,customer_name:$('customerName').value,customer_email:$('customerEmail').value})});$('bookingMessage').textContent=`Booking #${item.id} confirmed.`;e.target.reset()}catch(err){$('bookingMessage').textContent=err.message;$('bookingMessage').className='message error'}};

async function auth(form,path){try{await api(path,{method:'POST',body:JSON.stringify(payload(form))});await loadDashboard()}catch(err){$('ownerMessage').textContent=err.message;$('ownerMessage').className='message error'}}
$('registerForm').onsubmit=e=>{e.preventDefault();auth(e.target,'/api/auth/register')};
$('loginForm').onsubmit=e=>{e.preventDefault();auth(e.target,'/api/auth/login')};
$('logoutBtn').onclick=async()=>{await api('/api/auth/logout',{method:'POST'});$('dashboard').hidden=true;$('authPanel').hidden=false};
$('profileForm').onsubmit=async e=>{e.preventDefault();await api('/api/owner/profile',{method:'PUT',body:JSON.stringify({business_name:$('businessName').value})});await loadDashboard()};
$('serviceForm').onsubmit=async e=>{e.preventDefault();await api('/api/owner/services',{method:'POST',body:JSON.stringify({name:$('serviceName').value,duration_minutes:Number($('serviceDuration').value),price:Number($('servicePrice').value)})});e.target.reset();await loadDashboard();await loadServices()};
async function updateBooking(id,status){await api(`/api/owner/bookings/${id}`,{method:'PATCH',body:JSON.stringify({status})});await loadDashboard()}
async function loadDashboard(){try{const d=await api('/api/owner/dashboard');$('authPanel').hidden=true;$('forgotPasswordForm').hidden=true;$('dashboard').hidden=false;$('businessName').value=d.profile.business_name||'';$('businessTitle').textContent=d.profile.business_name||'Your business';$('bookingList').innerHTML=d.bookings.length?d.bookings.map(b=>`<div class="booking"><div><strong>${b.customer_name}</strong><br>${b.service_name} · ${new Date(b.appointment_at).toLocaleString()}<br><small>${b.customer_email} · ${b.status}</small></div><select onchange="updateBooking(${b.id},this.value)"><option ${b.status==='confirmed'?'selected':''}>confirmed</option><option ${b.status==='completed'?'selected':''}>completed</option><option ${b.status==='cancelled'?'selected':''}>cancelled</option></select></div>`).join(''):'<p>No bookings yet.</p>'}catch(_){$('authPanel').hidden=false;$('dashboard').hidden=true}}
$('ownerForgotLink').onclick=()=>{$('authPanel').hidden=true;$('forgotPasswordForm').hidden=false};
$('backToSigninLink').onclick=()=>{$('forgotPasswordForm').hidden=true;$('authPanel').hidden=false};
$('forgotPasswordForm').onsubmit=async e=>{e.preventDefault();try{const data=await api('/api/auth/forgot-password',{method:'POST',body:JSON.stringify({email:$('forgotEmail').value})});$('ownerMessage').textContent=data.message;$('ownerMessage').className='message'}catch(err){$('ownerMessage').textContent=err.message;$('ownerMessage').className='message error'}};

async function customerAuth(form,path){try{await api(path,{method:'POST',body:JSON.stringify(payload(form))});await loadCustomerDashboard()}catch(err){$('customerMessage').textContent=err.message;$('customerMessage').className='message error'}}
$('customerRegisterForm').onsubmit=e=>{e.preventDefault();customerAuth(e.target,'/api/customer/auth/register')};
$('customerLoginForm').onsubmit=e=>{e.preventDefault();customerAuth(e.target,'/api/customer/auth/login')};
$('customerLogoutBtn').onclick=async()=>{await api('/api/customer/auth/logout',{method:'POST'});$('customerDashboard').hidden=true;$('customerAuthPanel').hidden=false};
$('customerForgotLink').onclick=()=>{$('customerAuthPanel').hidden=true;$('customerForgotForm').hidden=false};
$('customerBackToSigninLink').onclick=()=>{$('customerForgotForm').hidden=true;$('customerAuthPanel').hidden=false};
$('customerForgotForm').onsubmit=async e=>{e.preventDefault();try{const data=await api('/api/customer/auth/forgot-password',{method:'POST',body:JSON.stringify({email:$('customerForgotEmail').value})});$('customerMessage').textContent=data.message;$('customerMessage').className='message'}catch(err){$('customerMessage').textContent=err.message;$('customerMessage').className='message error'}};
async function loadCustomerDashboard(){try{const bookings=await api('/api/customer/bookings');$('customerAuthPanel').hidden=true;$('customerForgotForm').hidden=true;$('customerDashboard').hidden=false;$('customerBookingList').innerHTML=bookings.length?bookings.map(b=>`<div class="booking"><div><strong>${b.service_name}</strong><br>${new Date(b.appointment_at).toLocaleString()}<br><small>${b.status}</small></div></div>`).join(''):'<p>No bookings yet.</p>'}catch(_){$('customerAuthPanel').hidden=false;$('customerDashboard').hidden=true}}

const resetParams=new URLSearchParams(location.search);
const resetToken=resetParams.get('token');
const resetType=resetParams.get('type')==='customer'?'customer':'owner';
if(resetToken){
  showView('resetPassword');
  $('resetPasswordForm').onsubmit=async e=>{e.preventDefault();try{const path=resetType==='customer'?'/api/customer/auth/reset-password':'/api/auth/reset-password';const data=await api(path,{method:'POST',body:JSON.stringify({token:resetToken,new_password:$('newPassword').value})});$('resetMessage').textContent=data.message}catch(err){$('resetMessage').textContent=err.message;$('resetMessage').className='message error'}};
}
loadServices();
