
  document.addEventListener('DOMContentLoaded', function() {
  var calendarEl = document.getElementById('calendar');
  var modalEvento = new bootstrap.Modal(document.getElementById('modalEvento'));
  var formEvento = document.getElementById('formEvento');
  var inputTitulo = document.getElementById('eventoTitulo');
  var inputFecha = document.getElementById('eventoFecha');
  var inputCorreo = document.getElementById('eventoCorreo');
  var inputDescripcion = document.getElementById('eventoDescripcion');
  var fechaSeleccionada = null;

  // Modal y formulario para enviar correo
  var modalCorreo = new bootstrap.Modal(document.getElementById('modalCorreo'));
  var formEnviarCorreo = document.getElementById('formEnviarCorreo');
  var correoDestino = document.getElementById('correoDestino');
  var archivosCorreo = document.getElementById('archivosCorreo');
  var correoEventoId = document.getElementById('correoEventoId');

  var calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: 'dayGridMonth',
    locale: 'es',
    selectable: true,
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'dayGridMonth,timeGridWeek'
    },
    events: eventos,
    height: 250, // <- ajusta la altura del calendario
    dateClick: function(info) {
      fechaSeleccionada = info.dateStr;
      inputFecha.value = fechaSeleccionada;
      inputTitulo.value = '';
      inputDescripcion.value = '';
      modalEvento.show();
    },
    eventClick: function(info) {
      document.querySelectorAll('.list-group-item.selected').forEach(function(el) {
        el.classList.remove('selected');
      });
      var li = document.querySelector('.list-group-item[data-id="' + info.event.id + '"]');
      if (li) {
        li.classList.add('selected');
        li.scrollIntoView({behavior: "smooth", block: "center"});
      } else {
        alert('El evento seleccionado no está visible en el periodo actual.');
      }
    },
    eventDidMount: function(info) {
      info.el.setAttribute('title', info.event.title);
    }
  });

  // Eliminar evento desde la lista
  document.querySelectorAll('.btn-eliminar').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var li = btn.closest('li');
      var eventoId = li.getAttribute('data-id');
      if (confirm('¿Eliminar este evento?')) {
        fetch(`/evento/eliminar/${eventoId}/`, {
          method: "POST",
          headers: {"X-CSRFToken": csrfToken}
        })
        .then(r => r.json())
        .then(data => {
          if (data.ok) {
            li.remove();
            var eventObj = calendar.getEventById(eventoId);
            if (eventObj) eventObj.remove();
          } else {
            alert('No se pudo eliminar');
          }
        });
      }
    });
  });

  // Mostrar modal para enviar correo con adjunto
  document.querySelectorAll('.btn-enviar-correo').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var li = btn.closest('li');
      var eventoId = li.getAttribute('data-id');
      correoEventoId.value = eventoId;
      correoDestino.value = '';
      archivosCorreo.value = '';
      modalCorreo.show();
    });
  });

  // Enviar correo con adjuntos
  formEnviarCorreo.addEventListener('submit', function(e) {
    e.preventDefault();
    var eventoId = correoEventoId.value;
    var formData = new FormData(formEnviarCorreo);
    fetch(`/evento/enviar_correo/${eventoId}/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken
      },
      body: formData
    })
    .then(r => r.json())
    .then(data => {
      if (data.ok) {
        alert('Correo enviado correctamente.');
        modalCorreo.hide();
      } else {
        alert('No se pudo enviar el correo.');
      }
    });
  });

  formEvento.addEventListener('submit', function(e) {
    e.preventDefault();
    fetch(urlCrearEvento, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken
      },
      body: JSON.stringify({
        titulo: inputTitulo.value,
        fecha: inputFecha.value,
        descripcion: inputDescripcion.value
      })
    })
    .then(response => response.json())
    .then(data => {
      if (data.ok) {
        calendar.addEvent({
          title: inputTitulo.value,
          start: inputFecha.value,
          allDay: true,
          id: data.id
        });
        const lista = document.querySelector('.list-group.list-group-flush');
        const li = document.createElement('li');
        li.className = 'list-group-item';
        li.setAttribute('data-id', data.id);
        li.innerHTML = `<strong>${inputFecha.value.split('-').reverse().join(' ')}</strong><br>
                        ${inputTitulo.value}<br>
                        <small class="text-muted">${inputDescripcion.value}</small>
                        <div class="mt-2">
                          <button class="btn btn-sm btn-danger btn-eliminar">Eliminar</button>
                          <button class="btn btn-sm btn-info btn-enviar-correo">Enviar correo</button>
                        </div>`;
        if (lista.querySelector('.text-muted')) {
          lista.innerHTML = '';
        }
        lista.prepend(li);
        // Añade el listener al nuevo botón eliminar
        li.querySelector('.btn-eliminar').addEventListener('click', function() {
          if (confirm('¿Eliminar este evento?')) {
            fetch(`/evento/eliminar/${data.id}/`, {
              method: "POST",
              headers: {"X-CSRFToken": csrfToken}
            })
            .then(r => r.json())
            .then(data2 => {
              if (data2.ok) {
                li.remove();
                var eventObj = calendar.getEventById(data.id.toString());
                if (eventObj) eventObj.remove();
              } else {
                alert('No se pudo eliminar');
              }
            });
          }
        });
        // Añade el listener al nuevo botón enviar correo
        li.querySelector('.btn-enviar-correo').addEventListener('click', function() {
          correoEventoId.value = data.id;
          correoDestino.value = '';
          archivosCorreo.value = '';
          modalCorreo.show();
        });
        modalEvento.hide();
        alert('Evento registrado');
      } else {
        alert('Error al registrar el evento.');
      }
    });
  });

  calendar.render();
});