let calendarInstance = null;
let currentProfessionals = []; // Armazena os dados para acesso seguro à jornada

document.addEventListener('DOMContentLoaded', function() {
    // 1. Máscara Premium de Telefone
    const phoneInput = document.getElementById('client-phone');
    if(phoneInput && typeof Inputmask !== "undefined") {
        Inputmask({
            mask: "(99) 9 9999-9999",
            placeholder: "_",
            showMaskOnHover: false,
            showMaskOnFocus: true
        }).mask(phoneInput);
    }
    
    // Inicializa o calendário (vazio até selecionar profissional)
    initCalendar();
});

// Estado Global do Agendamento
const bookingState = {
    categoriaId: null, 
    servicoId: null, 
    profissionalId: null,
    data: null, 
    hora: null, 
    resumo: {}
};

// --- FUNÇÕES UTILITÁRIAS ---

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

// --- PASSO 1: SELECIONAR CATEGORIA ---
function selectCategory(id) {
    bookingState.categoriaId = id;
    showLoader(true);
    
    // Busca os serviços da categoria selecionada
    fetch(`/api/get_services/?categoria_id=${id}`)
        .then(res => res.json())
        .then(data => {
            const list = document.getElementById('services-list');
            
            // GERAÇÃO DOS CARDS DE SERVIÇO (Quadrados, Centralizados e com Ícones)
            list.innerHTML = data.map(s => {
                // Lógica de Ícone: Usa a imagem se existir, senão usa um ícone padrão
                const iconHtml = s.icone_url 
                    ? `<img src="${s.icone_url}" class="w-12 h-12 object-contain mb-3 drop-shadow-sm group-hover:scale-110 transition-transform">`
                    : `<div class="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 mb-3 group-hover:scale-110 transition-transform"><i class="fa-solid fa-star text-xl"></i></div>`;

                return `
                <div onclick="selectService(${s.id}, '${s.nome}', '${s.preco}', '${s.tempo}')" 
                     class="group aspect-square flex flex-col items-center justify-center p-6 bg-white border border-slate-100 rounded-[2.5rem] cursor-pointer hover:shadow-xl hover:border-blue-500 transition-all relative overflow-hidden text-center">
                    
                    <div class="absolute inset-0 bg-blue-50 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                    
                    <div class="relative z-10 flex flex-col items-center">
                        ${iconHtml}
                        
                        <h4 class="font-bold text-slate-800 text-lg leading-tight group-hover:text-blue-600 transition-colors mb-1">${s.nome}</h4>
                        
                        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest bg-white/60 px-2 py-1 rounded-lg border border-slate-100 group-hover:border-blue-200 transition-colors">
                            ${s.tempo} min
                        </span>
                        
                        <div class="mt-3 text-xl font-black text-slate-900 group-hover:text-blue-700">R$ ${s.preco}</div>
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
    
    // Busca profissionais habilitados para este serviço
    fetch(`/api/get_professionals/?servico_id=${id}`)
        .then(res => res.json())
        .then(data => {
            currentProfessionals = data; // Salva para uso posterior (verificação de dias úteis)
            const grid = document.getElementById('professionals-grid');
            grid.innerHTML = '';
            
            data.forEach(p => {
                const photo = p.foto_url || `https://ui-avatars.com/api/?name=${p.nome}&background=3b82f6&color=fff&bold=true`;
                const card = document.createElement('div');
                card.className = "flex items-center p-6 bg-white border border-slate-100 rounded-[2rem] cursor-pointer hover:shadow-xl hover:border-blue-500 transition-all group";
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

// --- PASSO 3: SELECIONAR PROFISSIONAL ---
function selectProfessional(id, nome) {
    bookingState.profissionalId = id;
    bookingState.resumo.profissional = nome;
    
    // Lógica para desabilitar dias que o profissional NÃO trabalha
    const prof = currentProfessionals.find(p => p.id === id);
    const jornada = prof ? (prof.jornada || {}) : {};
    
    const dayMap = { 'dom': 0, 'seg': 1, 'ter': 2, 'qua': 3, 'qui': 4, 'sex': 5, 'sab': 6 };
    const workingDays = Object.keys(jornada).map(day => dayMap[day]);

    // Atualiza o calendário com as regras do profissional
    if(calendarInstance) {
        calendarInstance.set('enable', [
            function(date) { 
                if (workingDays.length === 0) return true; // Se não tiver jornada configurada, libera tudo
                return workingDays.includes(date.getDay()); 
            }
        ]);
        // Limpa seleção anterior
        calendarInstance.clear();
    }
    
    // Limpa horários anteriores
    document.getElementById('time-slots').innerHTML = '<div class="col-span-2 py-16 text-center text-slate-300 border-2 border-dashed border-slate-100 rounded-[2rem] italic">Escolha um dia no calendário</div>';
    
    showStep(4);
    
    // Força atualização do tamanho do calendário (bug visual do flatpickr em abas ocultas)
    setTimeout(() => calendarInstance.redraw(), 100);
}

// --- INICIALIZAÇÃO DO CALENDÁRIO ---
function initCalendar() {
    const calEl = document.getElementById('calendar-inline');
    if(calEl) {
        // Pega o limite definido no Template HTML. Se não existir, usa 30 dias por padrão.
        const diasLimite = (typeof LIMITE_AGENDAMENTO_DIAS !== 'undefined') ? LIMITE_AGENDAMENTO_DIAS : 30;

        calendarInstance = flatpickr(calEl, {
            inline: true, 
            minDate: "today", 
            // Limita a navegação do calendário conforme configuração da empresa
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
    container.innerHTML = '<div class="col-span-2 text-center py-10 animate-pulse text-slate-300 font-bold text-[11px] uppercase tracking-widest">Consultando...</div>';

    fetch(`/api/get_slots/?data=${dateStr}&profissional=${bookingState.profissionalId}&servico=${bookingState.servicoId}`)
        .then(res => res.json())
        .then(data => {
            container.innerHTML = '';
            
            // Tratamento de erro vindo do backend (ex: data fora do limite)
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
    document.getElementById('summary-datetime').innerText = `${bookingState.data} às ${hora}`;
    document.getElementById('summary-price').innerText = `R$ ${bookingState.resumo.preco}`;
    showStep(5);
}

// --- PASSO 5: CONFIRMAR AGENDAMENTO ---
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

// Função auxiliar para pegar o token CSRF
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