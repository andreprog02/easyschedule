let calendarInstance = null;
let currentProfessionals = []; // Armazena os dados para acesso seguro

document.addEventListener('DOMContentLoaded', function() {
    // 1. Máscara Premium de Telefone: (00) 0 0000-0000
    const phoneInput = document.getElementById('client-phone');
    if(phoneInput && typeof Inputmask !== "undefined") {
        Inputmask({
            mask: "(99) 9 9999-9999",
            placeholder: "_",
            showMaskOnHover: false,
            showMaskOnFocus: true
        }).mask(phoneInput);
    }
    initCalendar();
});

const bookingState = {
    categoriaId: null, servicoId: null, profissionalId: null,
    data: null, hora: null, resumo: {}
};

function showLoader(show) {
    const loader = document.getElementById('global-loader');
    if(loader) loader.style.display = show ? 'flex' : 'none';
}

function updateStepper(step) {
    const progress = (step - 1) * 25;
    const bar = document.getElementById('progress-bar');
    if(bar) bar.style.width = `${progress}%`;
    
    for(let i = 1; i <= 5; i++) {
        const circle = document.getElementById(`circle-step-${i}`);
        if(circle) {
            if(i <= step) circle.classList.add('border-blue-500', 'text-blue-500', 'bg-blue-50');
            else circle.classList.remove('border-blue-500', 'text-blue-500', 'bg-blue-50');
        }
    }
}

function showStep(stepNumber) {
    document.querySelectorAll('.step-content').forEach(el => el.classList.remove('active'));
    const target = document.getElementById(`step-${stepNumber}`);
    if(target) {
        target.classList.add('active');
        updateStepper(stepNumber);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function prevStep(num) { showStep(num); }

// --- PASSO 1: Selecionar Categoria ---
function selectCategory(id) {
    bookingState.categoriaId = id;
    showLoader(true);
    // REMOVIDO o prefixo /agendamento/ pois as urls estão na raiz
    fetch(`/api/get_services/?categoria_id=${id}`)
        .then(res => res.json())
        .then(data => {
            const list = document.getElementById('services-list');
            list.innerHTML = data.map(s => `
                <div onclick="selectService(${s.id}, '${s.nome}', '${s.preco}', '${s.tempo}')" 
                     class="flex justify-between items-center p-6 bg-white border border-slate-100 rounded-[2rem] cursor-pointer hover:shadow-xl hover:border-blue-500 transition-all group">
                    <div>
                        <h4 class="font-bold text-slate-800 group-hover:text-blue-500 transition-colors">${s.nome}</h4>
                        <span class="text-[11px] font-bold text-slate-400 uppercase tracking-widest mt-1 inline-block">${s.tempo} min</span>
                    </div>
                    <div class="text-xl font-black text-slate-900">R$ ${s.preco}</div>
                </div>
            `).join('');
            showLoader(false);
            showStep(2);
        }).catch(() => showLoader(false));
}

// --- PASSO 2: Selecionar Serviço ---
function selectService(id, nome, preco, tempo) {
    bookingState.servicoId = id;
    bookingState.resumo.servico = nome;
    bookingState.resumo.preco = preco;
    showLoader(true);
    
    fetch(`/api/get_professionals/?servico_id=${id}`)
        .then(res => res.json())
        .then(data => {
            currentProfessionals = data; // Guarda os profissionais para o próximo passo
            const grid = document.getElementById('professionals-grid');
            grid.innerHTML = '';
            
            data.forEach(p => {
                const photo = p.foto_url || `https://ui-avatars.com/api/?name=${p.nome}&background=3b82f6&color=fff&bold=true`;
                const card = document.createElement('div');
                card.className = "flex items-center p-6 bg-white border border-slate-100 rounded-[2rem] cursor-pointer hover:shadow-xl hover:border-blue-500 transition-all group";
                
                // Usamos o ID para buscar os dados da jornada de forma segura no selectProfessional
                card.onclick = () => selectProfessional(p.id, p.nome);
                
                card.innerHTML = `
                    <img src="${photo}" class="w-14 h-14 rounded-2xl object-cover shadow-sm group-hover:scale-105 transition-transform">
                    <div class="ml-5">
                        <h4 class="font-bold text-slate-800 group-hover:text-blue-500 transition-colors">${p.nome}</h4>
                        <p class="text-[11px] text-blue-500 font-bold uppercase tracking-widest">${p.especialidade || 'Especialista'}</p>
                    </div>
                `;
                grid.appendChild(card);
            });
            showLoader(false);
            showStep(3);
        }).catch(() => showLoader(false));
}

// --- PASSO 3: Selecionar Profissional e Bloquear Calendário ---
function selectProfessional(id, nome) {
    bookingState.profissionalId = id;
    bookingState.resumo.profissional = nome;
    
    // Busca os dados da jornada no array que salvamos no passo anterior
    const prof = currentProfessionals.find(p => p.id === id);
    const jornada = prof ? (prof.jornada || {}) : {};
    
    const dayMap = { 'dom': 0, 'seg': 1, 'ter': 2, 'qua': 3, 'qui': 4, 'sex': 5, 'sab': 6 };
    const workingDays = Object.keys(jornada).map(day => dayMap[day]);

    if(calendarInstance) {
        calendarInstance.set('enable', [
            function(date) { 
                // Se o profissional não tiver jornada, permite todos os dias para não travar o fluxo
                if (workingDays.length === 0) return true;
                return workingDays.includes(date.getDay()); 
            }
        ]);
    }
    showStep(4);
}

function initCalendar() {
    const calEl = document.getElementById('calendar-inline');
    if(calEl) {
        calendarInstance = flatpickr(calEl, {
            inline: true, minDate: "today", locale: "pt",
            onChange: (selectedDates, dateStr) => fetchTimeSlots(dateStr)
        });
    }
}

// --- PASSO 4: Consultar Horários ---
function fetchTimeSlots(dateStr) {
    bookingState.data = dateStr;
    const container = document.getElementById('time-slots');
    container.innerHTML = '<div class="col-span-2 text-center py-10 animate-pulse text-slate-300 font-bold text-[11px] uppercase tracking-widest">Consultando...</div>';

    fetch(`/api/get_slots/?data=${dateStr}&profissional=${bookingState.profissionalId}&servico=${bookingState.servicoId}`)
        .then(res => res.json())
        .then(data => {
            container.innerHTML = '';
            if(!data.slots || data.slots.length === 0) {
                container.innerHTML = '<div class="col-span-2 py-12 text-center text-red-400 font-bold">Sem horários livres.</div>';
                return;
            }
            data.slots.forEach(slot => {
                const btn = document.createElement('button');
                btn.className = `py-4 border rounded-2xl font-bold text-sm transition-all duration-300 shadow-sm ${slot.disponivel ? "bg-white border-slate-100 text-slate-700 hover:bg-blue-600 hover:text-white" : "bg-slate-50 border-transparent text-slate-300 line-through cursor-not-allowed opacity-50"}`;
                btn.innerText = slot.hora;
                if(slot.disponivel) btn.onclick = () => selectTime(slot.hora);
                else btn.disabled = true;
                container.appendChild(btn);
            });
        });
}

function selectTime(hora) {
    bookingState.hora = hora;
    document.getElementById('summary-service').innerText = bookingState.resumo.servico;
    document.getElementById('summary-professional').innerText = bookingState.resumo.profissional;
    document.getElementById('summary-datetime').innerText = `${bookingState.data} às ${hora}`;
    document.getElementById('summary-price').innerText = `R$ ${bookingState.resumo.preco}`;
    showStep(5);
}

function confirmBooking() {
    const nome = document.getElementById('client-name').value;
    const telefone = document.getElementById('client-phone').value;

    if (!nome || !telefone) {
        Swal.fire('Atenção', 'Informe seu nome e WhatsApp para finalizar.', 'info');
        return;
    }

    showLoader(true);
    fetch('/api/confirm_booking/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        body: JSON.stringify({
            profissional_id: bookingState.profissionalId,
            servico_id: bookingState.servicoId,
            data: bookingState.data,
            hora: bookingState.hora,
            cliente_nome: nome,
            cliente_telefone: telefone
        })
    })
    .then(res => res.json())
    .then(data => {
        showLoader(false);
        if(data.status === 'success') {
            Swal.fire('Agendado!', 'Seu horário foi reservado com sucesso.', 'success')
                .then(() => location.reload());
        } else {
            Swal.fire('Erro', data.message, 'error');
        }
    }).catch(() => showLoader(false));
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}