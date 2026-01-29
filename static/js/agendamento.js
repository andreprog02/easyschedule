let calendarInstance = null;
let currentProfessionals = []; 

document.addEventListener('DOMContentLoaded', function() {
    // Máscara de Telefone
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

// --- FUNÇÕES DE FORMATAÇÃO (BRL e DATA) ---
function formatMoney(valor) {
    if (!valor) return "0,00";
    return parseFloat(valor).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDateBR(dataISO) {
    if (!dataISO) return "";
    const [year, month, day] = dataISO.split('-');
    return `${day}/${month}/${year}`;
}

// --- FUNÇÕES DE INTERFACE ---
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

// --- PASSO 1: SELECIONAR CATEGORIA (Cards Quadrados + Ícones Grandes + Fundo Transparente) ---
function selectCategory(id) {
    bookingState.categoriaId = id;
    showLoader(true);
    
    fetch(`/api/get_services/?categoria_id=${id}`)
        .then(res => res.json())
        .then(data => {
            const list = document.getElementById('services-list');
            
            // GERAÇÃO DOS CARDS DE SERVIÇO
            list.innerHTML = data.map(s => {
                
                // ALTERAÇÃO AQUI: Adicionada a classe 'mix-blend-multiply'
                // Isso faz o branco da imagem "sumir" e se misturar com o fundo do cartão
                const iconContent = s.icone_url 
                    ? `<img src="${s.icone_url}" class="w-full h-full object-contain drop-shadow-sm mix-blend-multiply">`
                    : `<i class="fa-solid fa-scissors text-4xl"></i>`; 

                return `
                <div onclick="selectService(${s.id}, '${s.nome}', '${s.preco}', '${s.tempo}')" 
                     class="group aspect-square flex flex-col items-center justify-center p-4 bg-white border border-slate-100 rounded-[2.5rem] cursor-pointer hover:shadow-xl hover:border-blue-500 transition-all duration-300 relative overflow-hidden text-center">
                    
                    <div class="absolute inset-0 bg-blue-50 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                    
                    <div class="relative z-10 flex flex-col items-center w-full h-full justify-center">
                        
                        <div class="relative w-36 h-36 mb-2 rounded-2xl flex items-center justify-center text-blue-600 transition-transform group-hover:scale-110">
                            ${iconContent}
                        </div>

                        <h4 class="font-bold text-slate-800 text-lg leading-tight group-hover:text-blue-600 transition-colors mb-1 line-clamp-2">
                            ${s.nome}
                        </h4>
                        
                        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest bg-white/60 px-2 py-1 rounded-lg border border-slate-100 group-hover:border-blue-200 transition-colors">
                            ${s.tempo} min
                        </span>
                        
                        <div class="mt-2 text-xl font-black text-slate-900 group-hover:text-blue-700">
                            R$ ${formatMoney(s.preco)}
                        </div>
                    </div>
                </div>
                `;
            }).join('');
            
            showLoader(false);
            showStep(2);
        }).catch((err) => {
            console.error(err);
            showLoader(false);
        });
}

// --- PASSO 2: SELECIONAR SERVIÇO ---
function selectService(id, nome, preco, tempo) {
    bookingState.servicoId = id;
    bookingState.resumo.servico = nome;
    bookingState.resumo.preco = preco; 
    showLoader(true);
    
    fetch(`/api/get_professionals/?servico_id=${id}`)
        .then(res => res.json())
        .then(data => {
            currentProfessionals = data; 
            const grid = document.getElementById('professionals-grid');
            
            grid.className = "grid grid-cols-2 md:grid-cols-3 gap-6";
            grid.innerHTML = '';
            
            data.forEach(p => {
                const photo = p.foto_url || `https://ui-avatars.com/api/?name=${p.nome}&background=3b82f6&color=fff&bold=true`;
                const card = document.createElement('div');
                
                card.className = "group bg-white border border-slate-100 rounded-[2.5rem] cursor-pointer hover:shadow-xl hover:border-blue-500 transition-all overflow-hidden flex flex-col";
                card.onclick = () => selectProfessional(p.id, p.nome);
                
                card.innerHTML = `
                    <div class="relative w-full aspect-square bg-slate-50 overflow-hidden">
                        <img src="${photo}" class="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-500">
                    </div>
                    <div class="p-6 text-center flex flex-col justify-center flex-grow">
                        <h4 class="font-bold text-slate-900 text-lg group-hover:text-blue-600 transition-colors mb-2 leading-tight">${p.nome}</h4>
                        <div>
                            <span class="inline-block px-3 py-1 bg-blue-50 text-blue-600 text-[10px] font-bold uppercase tracking-wider rounded-full border border-blue-100">
                                ${p.especialidade || 'Especialista'}
                            </span>
                        </div>
                    </div>
                `;
                grid.appendChild(card);
            });
            showLoader(false);
            showStep(3);
        }).catch(() => showLoader(false));
}

// --- PASSO 3: SELECIONAR PROFISSIONAL ---
function selectProfessional(id, nome) {
    bookingState.profissionalId = id;
    bookingState.resumo.profissional = nome;
    
    const prof = currentProfessionals.find(p => p.id === id);
    const jornada = prof ? (prof.jornada || {}) : {};
    
    const dayMap = { 'dom': 0, 'seg': 1, 'ter': 2, 'qua': 3, 'qui': 4, 'sex': 5, 'sab': 6 };
    const workingDays = Object.keys(jornada).map(day => dayMap[day]);

    if(calendarInstance) {
        calendarInstance.set('enable', [
            function(date) { 
                if (workingDays.length === 0) return true; 
                return workingDays.includes(date.getDay()); 
            }
        ]);
        calendarInstance.clear();
    }
    
    document.getElementById('time-slots').innerHTML = '<div class="col-span-2 py-16 text-center text-slate-300 border-2 border-dashed border-slate-100 rounded-[2rem] italic">Escolha um dia no calendário</div>';
    
    showStep(4);
    setTimeout(() => calendarInstance.redraw(), 100);
}

function initCalendar() {
    const calEl = document.getElementById('calendar-inline');
    if(calEl) {
        const diasLimite = (typeof LIMITE_AGENDAMENTO_DIAS !== 'undefined') ? LIMITE_AGENDAMENTO_DIAS : 30;

        calendarInstance = flatpickr(calEl, {
            inline: true, 
            minDate: "today", 
            maxDate: new Date().fp_incr(diasLimite),
            locale: "pt",
            onChange: (selectedDates, dateStr) => fetchTimeSlots(dateStr)
        });
    }
}

// --- PASSO 4: CONSULTAR HORÁRIOS ---
function fetchTimeSlots(dateStr) {
    bookingState.data = dateStr;
    const container = document.getElementById('time-slots');
    
    const displayDate = document.getElementById('selected-date-display');
    if(displayDate) displayDate.innerText = `Horários para ${formatDateBR(dateStr)}`;

    container.innerHTML = '<div class="col-span-2 text-center py-10 animate-pulse text-slate-300 font-bold text-[11px] uppercase tracking-widest">Consultando...</div>';

    fetch(`/api/get_slots/?data=${dateStr}&profissional=${bookingState.profissionalId}&servico=${bookingState.servicoId}`)
        .then(res => res.json())
        .then(data => {
            container.innerHTML = '';
            
            if(data.message) {
                 container.innerHTML = `<div class="col-span-2 py-12 text-center text-red-400 font-bold text-sm">${data.message}</div>`;
                 return;
            }

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
        }).catch(err => {
            console.error(err);
            container.innerHTML = '<div class="col-span-2 py-12 text-center text-red-400 font-bold">Erro ao buscar horários.</div>';
        });
}

function selectTime(hora) {
    bookingState.hora = hora;
    
    document.getElementById('summary-service').innerText = bookingState.resumo.servico;
    document.getElementById('summary-professional').innerText = bookingState.resumo.profissional;
    document.getElementById('summary-datetime').innerText = `${formatDateBR(bookingState.data)} às ${hora}`;
    document.getElementById('summary-price').innerText = `R$ ${formatMoney(bookingState.resumo.preco)}`;
    
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
            Swal.fire({
                title: 'Agendado!',
                text: 'Seu horário foi reservado com sucesso.',
                icon: 'success',
                confirmButtonText: 'OK',
                confirmButtonColor: '#3b82f6'
            }).then(() => location.reload());
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