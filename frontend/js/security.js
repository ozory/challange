/* Camada 1 de segurança (cliente): validação rápida antes de enviar ao backend.
 * É apenas UX + redução de ruído; a validação autoritativa é feita no backend.
 * Desligar: window.FG_SECURITY_ENABLED = false (antes de carregar este script). */
(function () {
  var CONFIG = {
    enabled: window.FG_SECURITY_ENABLED !== false,
    maxTextLength: 2000,
    maxFileBytes: 5 * 1024 * 1024
  };

  // Mesmos padrões de alto risco do backend (prompt injection / markup ativo)
  var PATTERNS = [
    /ignor(e|a|ar)\s+(todas?\s+)?(as\s+|your\s+|all\s+|the\s+|suas\s+)*(instru|regras|diretriz|previous|prior|above|anterior)/i,
    /(esque(c|ç)a|disregard|forget)\s+(tudo|todas?|all|your|as\s+instru|previous)/i,
    /\b(system|developer)\s*(prompt|message|role)\b/i,
    /(prompt|instru(c|ç)(ões|oes))\s+(do\s+)?(sistema|interno|original)/i,
    /\byou\s+are\s+now\b|\bjailbreak\b|\bDAN\s+mode\b/i,
    /<\s*\/?\s*(script|iframe|object|embed|style|img|svg|link)\b/i,
    /javascript\s*:/i,
    /\bon(error|load|click)\s*=/i
  ];
  // eslint-disable-next-line no-control-regex
  var CONTROL = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f​-‏‪-‮⁠﻿]/g;

  function report(type, detail) {
    if (FG.api && FG.api.registrarEventoSeguranca) FG.api.registrarEventoSeguranca(type, detail);
  }

  /** Retorna { ok, texto, error }. */
  function validateText(texto) {
    if (!CONFIG.enabled) return { ok: true, texto: texto };
    var limpo = String(texto).replace(CONTROL, '').trim();
    if (!limpo) return { ok: false, error: 'Digite o texto da reclamação.' };
    if (limpo.length > CONFIG.maxTextLength) {
      report('TEXT_TOO_LONG', 'len=' + limpo.length);
      return { ok: false, error: 'O texto excede ' + CONFIG.maxTextLength + ' caracteres.' };
    }
    for (var i = 0; i < PATTERNS.length; i++) {
      if (PATTERNS[i].test(limpo)) {
        report('SUSPICIOUS_PATTERN', PATTERNS[i].source.slice(0, 40));
        return { ok: false, error: 'O texto contém conteúdo não permitido. Descreva apenas a sua reclamação.' };
      }
    }
    return { ok: true, texto: limpo };
  }

  /** Retorna { ok, error }. */
  function validateFile(file) {
    if (!CONFIG.enabled) return { ok: true };
    var reason = null;
    if (!/\.csv$/i.test(file.name)) reason = 'O arquivo deve ter extensão .csv.';
    else if (file.size > CONFIG.maxFileBytes) reason = 'O arquivo excede ' + (CONFIG.maxFileBytes / 1048576) + ' MB.';
    else if (file.size === 0) reason = 'O arquivo está vazio.';
    if (reason) {
      report('CSV_REJECTED', reason);
      return { ok: false, error: reason };
    }
    return { ok: true };
  }

  window.FG = window.FG || {};
  window.FG.security = { config: CONFIG, validateText: validateText, validateFile: validateFile };
})();
