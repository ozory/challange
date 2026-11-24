/* Painel de chat: envia texto livre para /classify e exibe a análise. */
(function () {
  var el = FG.el, icon = FG.icon;

  function formatarHora(date) {
    return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  }

  function createChat(onNewAnalysis) {
    var enviando = false;

    var messages = el('div', { class: 'chat-messages' });
    var errorSlot = el('div');
    var textarea = el('textarea', {
      class: 'input', rows: 3, maxlength: FG.security.config.maxTextLength, placeholder: 'Digite a reclamação do cliente aqui...',
      oninput: updateSendState,
      onkeydown: function (e) {
        // Enter envia; Shift+Enter quebra linha
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
      }
    });
    var sendBtn = el('button', { type: 'submit', class: 'btn btn-primary' },
      icon('send'), el('span', { class: 'btn-label-hide' }, 'Enviar'));
    var form = el('form', { class: 'chat-form', onsubmit: handleSubmit },
      el('div', { class: 'chat-form-row' }, textarea, sendBtn),
      el('p', { class: 'hint' }, 'Pressione Enter para enviar • Shift+Enter para nova linha'));

    var emptyState = el('div', { class: 'empty-state animate-fade-in' },
      icon('messageSquare', 'xl'), el('p', null, 'Envie sua primeira reclamação para começar'));
    messages.appendChild(emptyState);
    var typing = null;

    var clearBtn = el('button', {
      type: 'button', class: 'btn btn-ghost btn-icon danger', title: 'Limpar conversa', 'aria-label': 'Limpar conversa',
      onclick: clearChat
    }, icon('trash'));

    function updateSendState() {
      sendBtn.disabled = !textarea.value.trim() || enviando;
      clearBtn.disabled = enviando;
    }
    updateSendState();

    // Limpa a conversa e deixa o chat pronto para novas entradas
    function clearChat() {
      if (enviando) return;
      FG.clear(messages);
      messages.appendChild(emptyState);
      typing = null;
      showError(null);
      textarea.value = '';
      updateSendState();
      textarea.focus();
    }

    function scrollToBottom() {
      messages.scrollTo({ top: messages.scrollHeight, behavior: 'smooth' });
    }

    function addMessage(msg) {
      if (emptyState.parentNode) messages.removeChild(emptyState);
      var isUser = msg.tipo === 'user';

      var content;
      if (isUser) {
        content = el('p', null, msg.texto);
      } else if (msg.tipo === 'error') {
        content = el('div', { class: 'err' }, icon('alertCircle', 'sm'), el('span', null, msg.texto));
      } else {
        var d = msg.data;
        content = el('div', null,
          el('div', { class: 'badges' },
            el('span', { class: FG.urgenciaBadge(d.urgencia) }, d.urgencia),
            el('span', { class: FG.sentimentoBadge(d.sentimento) }, d.sentimento),
            el('span', { class: 'badge badge-primary' }, d.categoria),
            el('span', { class: 'badge badge-info' }, d.produto)),
          el('p', { class: 'summary' }, d.resumo),
          el('p', { class: 'ticket-id mono' }, 'ID: ' + d.id));
      }

      var row = el('div', { class: 'msg-row animate-fade-in' + (isUser ? ' user' : '') },
        el('div', { class: 'msg-wrap' },
          el('div', { class: 'msg-line' },
            el('div', { class: 'avatar' }, icon(isUser ? 'user' : 'bot')),
            el('div', { class: 'bubble' }, content)),
          el('p', { class: 'msg-time' }, formatarHora(new Date()))));

      messages.insertBefore(row, typing);
      scrollToBottom();
    }

    function setTyping(on) {
      if (on && !typing) {
        typing = el('div', { class: 'msg-row animate-fade-in' },
          el('div', { class: 'msg-line' },
            el('div', { class: 'avatar' }, icon('bot')),
            el('div', { class: 'bubble typing' }, icon('loader', 'sm', 'spin'), el('span', null, 'Analisando...'))));
        messages.appendChild(typing);
        scrollToBottom();
      } else if (!on && typing) {
        messages.removeChild(typing);
        typing = null;
      }
    }

    function showError(text) {
      FG.clear(errorSlot);
      if (text) {
        errorSlot.appendChild(el('div', { class: 'chat-error animate-slide-in' },
          icon('alertCircle'), el('span', null, text)));
      }
    }

    function handleSubmit(e) {
      e.preventDefault();
      var texto = textarea.value.trim();
      if (!texto || enviando) return;

      // Camada 1: validação no cliente antes de enviar
      var check = FG.security.validateText(texto);
      if (!check.ok) { showError(check.error); return; }
      texto = check.texto;

      textarea.value = '';
      showError(null);
      enviando = true;
      textarea.disabled = true;
      updateSendState();
      addMessage({ tipo: 'user', texto: texto });
      setTyping(true);

      FG.api.classificarReclamacao(texto).then(function (result) {
        if (result.success && result.data) {
          setTyping(false);
          addMessage({ tipo: 'ai', data: result.data });
          onNewAnalysis(result.data);
        } else {
          throw new Error(result.error || 'Erro na classificação');
        }
      }).catch(function (err) {
        console.error('Erro:', err);
        setTyping(false);
        showError(err.message);
        addMessage({ tipo: 'error', texto: 'Erro: ' + err.message });
      }).then(function () {
        enviando = false;
        textarea.disabled = false;
        updateSendState();
        textarea.focus();
      });
    }

    return el('div', { class: 'chat' },
      el('div', {
        class: 'panel-head chat-head',
        // estilo inline: garante o alinhamento mesmo se o styles.css vier do cache
        style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }
      },
        el('div', null,
          el('h2', { class: 'panel-title' }, icon('bot'), 'Chatbot de Triagem'),
          el('p', { class: 'text-xs text-muted', style: { marginTop: '0.25rem' } }, 'Digite uma reclamação em texto livre para análise imediata')),
        clearBtn),
      messages, errorSlot, form);
  }

  FG.createChat = createChat;
})();
