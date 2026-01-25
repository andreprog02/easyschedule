document.addEventListener('DOMContentLoaded', function() {
    // Inicializa Máscara de Telefone
    const phoneInput = document.getElementById('client-phone');
    if(phoneInput) {
        Inputmask("(99) 9 9999-9999").mask(phoneInput);
    }

    // Inicializa o Calendário (Flatpickr)
    initCalendar();
});

// --- Estado Global do Agendamento ---
const bookingState = {
    categoriaId: null,
    servicoId: null,
    profissionalId: null,
    data: null,
    hora: null,
    resumo: {}
};

// --- Navegação entre Passos ---
function showStep(stepNumber) {
    document.querySelectorAll('.step-content').forEach(el => el.classList.remove('active'));
    const currentStep = document.getElementById(`step-${stepNumber}`);
    if(currentStep) currentStep.classList.add('active');

    // Atualiza Barra de Progresso
    const progressMap = {1: '20%', 2: '40%', 3: '60%', 4: '80%', 5: '100%'};
    document.getElementById('progress-bar').style.width = progressMap[stepNumber];
}

function prevStep(targetStep) {
    showStep(targetStep);
}

function toggleLoader(show) {
    const loader = document.getElementById('global-loader');
    if(loader) loader.style.display = show ? 'flex' : 'none';
}

// --- Passo 1: Seleção de Categoria ---
function selectCategory(id) {
    bookingState.categoriaId = id;
    toggleLoader(true);

    fetch(`/api/get_services/?categoria_id=${id}`)
        .then(response => response.json())
        .then(data => {
            const listContainer = document.getElementById('services-list');
            listContainer.innerHTML = '';
            data.forEach(servico => {
                listContainer.innerHTML += `
                <div onclick="selectService(${servico.id}, '${servico.nome}', '${servico.preco}', '${servico.tempo}')" 
                     class="flex justify-between items-center p-4 border border-gray-200 rounded-lg cursor-pointer hover:border-accent hover:bg-blue-50 transition shadow-sm bg-white mb-3">
                    <div>
                        <h4 class="font-bold text-gray-800">${servico.nome}</h4>
                        <p class="text-sm text-gray-500"><i class="fa-regular fa-clock"></i> ${servico.tempo} min</p>
                    </div>
                    <div class="text-accent font-bold text-lg">R$ ${servico.preco}</div>
                </div>`;
            });
            toggleLoader(false);
            showStep(2);
        });
}

// --- Passo 2: Seleção de Serviço ---
function selectService(id, nome, preco, tempo) {
    bookingState.servicoId = id;
    bookingState.resumo.servico = nome;
    bookingState.resumo.preco = preco;
    toggleLoader(true);

    fetch(`/api/get_professionals/?servico_id=${id}`)
        .then(response => response.json())
        .then(data => {
            const grid = document.getElementById('professionals-grid');
            grid.innerHTML = '';
            data.forEach(prof => {
                const photo = prof.foto_url ? prof.foto_url : 'https://ui-avatars.com/api/?name=' + prof.nome;
                grid.innerHTML += `
                <div onclick="selectProfessional(${prof.id}, '${prof.nome}')" 
                     class="flex items-center p-4 border border-gray-200 rounded-lg cursor-pointer hover:border-accent hover:bg-blue-50 transition bg-white group">
                    <img src="${photo}" class="w-12 h-12 rounded-full object-cover">
                    <div class="ml-4 text-left">
                        <h4 class="font-bold text-gray-800">${prof.nome}</h4>
                        <p class="text-xs text-gray-500">${prof.especialidade || 'Especialista'}</p>
                    </div>
                </div>`;
            });
            toggleLoader(false);
            showStep(3);
        });
}

// --- Passo 3: Seleção de Profissional ---
function selectProfessional(id, nome) {
    bookingState.profissionalId = id;
    bookingState.resumo.profissional = nome;
    showStep(4);
}

// --- Passo 4: Data e Hora (A lógica de cores e traços está aqui) ---
function initCalendar() {
    flatpickr("#calendar-inline", {
        inline: true,
        minDate: "today",
        locale: "pt",
        onChange: function(selectedDates, dateStr) {
            fetchTimeSlots(dateStr);
        }
    });
}

function fetchTimeSlots(dateStr) {
    bookingState.data = dateStr;
    const slotsContainer = document.getElementById('time-slots');
    slotsContainer.innerHTML = '<div class="col-span-3 text-center py-4">Carregando horários...</div>';

    fetch(`/api/get_slots/?data=${dateStr}&profissional=${bookingState.profissionalId}&servico=${bookingState.servicoId}`)
        .then(response => response.json())
        .then(data => {
            slotsContainer.innerHTML = '';
            data.slots.forEach(slot => {
                // Se NÃO disponível: cor cinza, riscado e botão desativado
                const btnClass = slot.disponivel 
                    ? "bg-white border-green-500 text-green-700 hover:bg-green-50 cursor-pointer" 
                    : "bg-gray-100 border-gray-200 text-gray-400 cursor-not-allowed line-through opacity-50";
                
                const disabledAttr = slot.disponivel ? "" : "disabled";
                const onClickAttr = slot.disponivel ? `onclick="selectTime('${slot.hora}')"` : "";

                slotsContainer.innerHTML += `
                <button ${disabledAttr} ${onClickAttr} class="border rounded py-2 px-1 text-sm font-medium transition ${btnClass}">
                    ${slot.hora}
                </button>`;
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

// --- Passo 5: Confirmação Final ---
function confirmBooking() {
    const nome = document.getElementById('client-name').value;
    const telefone = document.getElementById('client-phone').value;

    if (!nome || !telefone) {
        Swal.fire('Atenção', 'Preencha seu nome e telefone.', 'warning');
        return;
    }

    toggleLoader(true);

    fetch('/api/confirm_booking/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            profissional_id: bookingState.profissionalId,
            servico_id: bookingState.servicoId,
            data: bookingState.data,
            hora: bookingState.hora,
            cliente_nome: nome,
            cliente_telefone: telefone
        })
    })
    .then(response => response.json())
    .then(data => {
        toggleLoader(false);
        if (data.status === 'success') {
            Swal.fire('Agendado!', `Código: ${data.codigo}`, 'success')
                .then(() => location.reload());
        } else {
            Swal.fire('Erro', data.message, 'error');
        }
    });
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