document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        // 1. Forçar texto escuro em TODOS os elementos dentro de .shell-module.active
        document.querySelectorAll('.shell-module.active').forEach(function(mod) {
            mod.querySelectorAll('*').forEach(function(el) {
                var cs = getComputedStyle(el);
                var bg = cs.backgroundColor;
                var color = cs.color;

                // Se o fundo é claro (branco, cinza claro, transparente)
                // e o texto também é claro → forçar texto escuro
                if (isLightBg(bg) && isLightColor(color)) {
                    var tag = el.tagName;
                    if (tag === 'H1' || tag === 'H2' || tag === 'H3' || tag === 'H4') {
                        el.style.setProperty('color', '#0D1B2A', 'important');
                    } else if (tag === 'TH') {
                        // Não mexer em thead
                    } else {
                        el.style.setProperty('color', '#333333', 'important');
                    }
                }
            });
        });

        // 2. Forçar banners com gradiente azul/rosa para fundo neutro
        document.querySelectorAll('[style*="linear-gradient"]').forEach(function(el) {
            var s = el.getAttribute('style') || '';
            if (s.indexOf('linear-gradient') > -1 && !isNavOrHeader(el)) {
                el.style.setProperty('background', '#f0faf9', 'important');
                el.style.setProperty('border-left', '4px solid #00C6BD', 'important');
                el.querySelectorAll('*').forEach(function(child) {
                    child.style.setProperty('color', '#0D1B2A', 'important');
                });
            }
        });

        // 3. Cards de alerta escuros → fundo branco
        document.querySelectorAll('.shell-module.active [style*="background"]').forEach(function(el) {
            var bg = getComputedStyle(el).backgroundColor;
            if (isDarkBg(bg) && !isNavOrHeader(el) && !isBadge(el)) {
                el.style.setProperty('background', '#FFFFFF', 'important');
                el.style.setProperty('border', '1px solid #E0E6EC', 'important');
                el.style.setProperty('box-shadow', '0 2px 8px rgba(0,0,0,0.06)', 'important');
            }
        });

        console.log('[DMD Fix] Cores corrigidas');
    }, 1500);

    // Re-executar fix a cada troca de aba
    window._dmdFixColors = function() {
        setTimeout(function() {
            document.querySelectorAll('.shell-module.active').forEach(function(mod) {
                // Pular mapa (deve ficar escuro)
                if (mod.id === 'mod-mapa') return;
                mod.querySelectorAll('*').forEach(function(el) {
                    var cs = getComputedStyle(el);
                    var bg = cs.backgroundColor;
                    var color = cs.color;
                    if (isLightBg(bg) && isLightColor(color)) {
                        var tag = el.tagName;
                        if (tag === 'H1' || tag === 'H2' || tag === 'H3' || tag === 'H4') {
                            el.style.setProperty('color', '#0D1B2A', 'important');
                        } else if (tag === 'TH') {
                            // Não mexer em thead
                        } else {
                            el.style.setProperty('color', '#333333', 'important');
                        }
                    }
                });
            });
            // Fix cards escuros
            document.querySelectorAll('.shell-module.active [style*="background"]').forEach(function(el) {
                var bg = getComputedStyle(el).backgroundColor;
                if (isDarkBg(bg) && !isNavOrHeader(el) && !isBadge(el)) {
                    el.style.setProperty('background', '#FFFFFF', 'important');
                    el.style.setProperty('border', '1px solid #E0E6EC', 'important');
                    el.style.setProperty('box-shadow', '0 2px 8px rgba(0,0,0,0.06)', 'important');
                }
            });
        }, 800);
    };

    function isLightBg(bg) {
        if (!bg || bg === 'transparent' || bg === 'rgba(0, 0, 0, 0)') return true;
        var m = bg.match(/\d+/g);
        if (!m) return true;
        var r = parseInt(m[0]), g = parseInt(m[1]), b = parseInt(m[2]);
        return (r + g + b) / 3 > 180;
    }
    function isLightColor(c) {
        if (!c) return false;
        var m = c.match(/\d+/g);
        if (!m) return false;
        var r = parseInt(m[0]), g = parseInt(m[1]), b = parseInt(m[2]);
        return (r + g + b) / 3 > 180;
    }
    function isDarkBg(bg) {
        if (!bg || bg === 'transparent' || bg === 'rgba(0, 0, 0, 0)') return false;
        var m = bg.match(/\d+/g);
        if (!m) return false;
        var r = parseInt(m[0]), g = parseInt(m[1]), b = parseInt(m[2]);
        return (r + g + b) / 3 < 80;
    }
    function isNavOrHeader(el) {
        var p = el;
        while (p) {
            var tag = (p.tagName || '').toLowerCase();
            var cls = (p.className || '').toLowerCase();
            if (tag === 'nav' || tag === 'header' || tag === 'thead' ||
                cls.indexOf('nav') > -1 || cls.indexOf('header') > -1 ||
                cls.indexOf('footer') > -1 || cls.indexOf('thead') > -1) return true;
            p = p.parentElement;
        }
        return false;
    }
    function isBadge(el) {
        var cls = (el.className || '').toLowerCase();
        var w = el.offsetWidth || 0;
        return cls.indexOf('badge') > -1 || (w < 120 && w > 20);
    }
});
