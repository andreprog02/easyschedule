let calendarInstance = null;

document.addEventListener('DOMContentLoaded', function() {
    initCalendar();
});

const bookingState = {
    categoriaId: null,
    servicoId: null,
    profissionalId: null,
    data: null,
    hora: null,
    resumo: {}
};

function updateStepper(step) {
    const progress = (step - 1) * 25;
    document.getElementById('progress-bar').style.width = `${progress}%`;
    for(let i = 1; i <= 5; i++) {
        const circle = document.getElementById(`circle-step-${i}`);
        if(circle) {
            if(i <= step) circle.classList.add('step-indicator-active');
            else circle.classList.remove('step-indicator-active');
        }
    }
}

function showStep(stepNumber) {
    document.querySelectorAll('.step-content').forEach(el => el.classList.remove('active'));
    document.getElementById(`step-${stepNumber}`).classList.add('active');
    updateStepper(stepNumber);
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function selectCategory(id) {
    bookingState.categoriaId = id;
    toggleLoader(true);
    fetch(`/api/get_services/?categoria_id=${id}`)
        .then(res => res.json())
        .then(data => {
            const list = document.getElementById('services-list');
            list.innerHTML = '';
            data.forEach(s => {
                const item = document.createElement('div');
                item.className = "flex justify-between items-center p-6 bg-white border border-gray-100 rounded-3xl cursor-pointer hover:shadow-xl hover:border-accent transition-all group";
                item.onclick = () => selectService(s.id, s.nome, s.preco, s.tempo);
                item.innerHTML = `
                    <div>
                        <h4 class="font-bold text-gray-800 group-hover:text-accent">${s.nome}</h4>
                        <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest">${s.tempo} MIN</span>
                    </div>
                    <div class="text-xl font-black text-gray-900">R$ ${s.preco}</div>
                `;
                list.appendChild(item);
            });
            toggleLoader(false);
            showStep(2);
        });
}

function selectService(id, nome, preco, tempo) {
    bookingState.servicoId = id;
    bookingState.resumo.servico = nome;
    bookingState.resumo.preco = preco;
    toggleLoader(true);
    fetch(`/api/get_professionals/?servico_id=${id}`)
        .then(res => res.json())
        .then(data => {
            const grid = document.getElementById('professionals-grid');
            grid.innerHTML = '';
            data.forEach(p => {
                const photo = p.foto_url || `https://ui-avatars.com/api/?name=${p.nome}&background=3b82f6&color=fff&bold=true`;
                const card = document.createElement('div');
                card.className = "flex items-center p-6 bg-white border border-gray-100 rounded-[2rem] cursor-pointer hover:shadow-xl hover:border-accent transition-all group";
                card.onclick = () => selectProfessional(p.id, p.nome, p.jornada || {});
                card.innerHTML = `
                    <img src="${photo}" class="w-16 h-16 rounded-2xl object-cover shadow-sm group-hover:scale-105 transition-transform">
                    <div class="ml-5">
                        <h4 class="font-black text-gray-800 group-hover:text-accent">${p.nome}</h4>
                        <p class="text-[10px] text-accent font-black uppercase tracking-widest">${p.especialidade || 'Especialista'}</p>
                    </div>
                `;
                grid.appendChild(card);
            });
            toggleLoader(false);
            showStep(3);
        });
}

function selectProfessional(id, nome, jornada) {
    bookingState.profissionalId = id;
    bookingState.resumo.profissional = nome;
    
    // BLOQUEIO DO CALENDÁRIO: Filtra os dias de trabalho (0=Dom, 1=Seg...)
    const dayMap = { 'dom': 0, 'seg': 1, 'ter': 2, 'qua': 3, 'qui': 4, 'sex': 5, 'sab': 6 };
    const workingDays = Object.keys(jornada).map(day => dayMap[day]);

    calendarInstance.set('enable', [
        function(date) {
            return workingDays.includes(date.getDay());
        }
    ]);
    showStep(4);
}

function initCalendar() {
    calendarInstance = flatpickr("#calendar-inline", {
        inline: true,
        minDate: "today",
        locale: "pt",
        onChange: (selectedDates, dateStr) => fetchTimeSlots(dateStr)
    });
}

function fetchTimeSlots(dateStr) {
    bookingState.data = dateStr;
    const container = document.getElementById('time-slots');
    container.innerHTML = '<div class="col-span-2 text-center py-10 animate-pulse text-gray-400 font-bold text-[10px]">CONSULTANDO AGENDA...</div>';

    fetch(`/api/get_slots/?data=${dateStr}&profissional=${bookingState.profissionalId}&servico=${bookingState.servicoId}`)
        .then(res => res.json())
        .then(data => {
            container.innerHTML = '';
            if(data.slots.length === 0) {
                container.innerHTML = '<div class="col-span-2 text-center py-10 text-red-400 font-bold">Sem horários.</div>';
                return;
            }
            data.slots.forEach(slot => {
                const btn = document.createElement('button');
                btn.className = `py-4 border rounded-2xl font-black text-xs transition-all duration-300 shadow-sm ${slot.disponivel ? "bg-white border-gray-100 text-gray-700 hover:bg-accent hover:text-white" : "bg-gray-50 border-transparent text-gray-300 line-through cursor-not-allowed opacity-50"}`;
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

function toggleLoader(show) {
    const loader = document.getElementById('global-loader');
    if(loader) loader.style.display = show ? 'flex' : 'none';
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