/* Shared card rendering + download (admin Card Studio & public share page) */
function cardEsc(s){ const d=document.createElement('div'); d.textContent = (s==null?'':s); return d.innerHTML; }

function buildCard(el, c, type){
    c = c || {};
    const accent = c.color || '#2d5a3d';
    const logo = c.logo || '/static/img/logo.jpg';
    const photo = c.photo || '';
    el.style.setProperty('--card-accent', accent);
    if(type === 'id'){
        el.className = 'card-render card-id';
        el.innerHTML = `
            <div class="cid-left"><div class="cid-photo">${photo?`<img src="${photo}" crossorigin="anonymous">`:'<span>🪪</span>'}</div></div>
            <div class="cid-right">
                <div class="cid-top"><img class="cid-logo" src="${logo}" crossorigin="anonymous"><span>${cardEsc(c.brand||'Nature by Regina')}</span></div>
                <div class="cid-badge">${cardEsc(c.title||'VIP MEMBER')}</div>
                <h3 class="cid-name">${cardEsc(c.name||'Member Name')}</h3>
                <div class="cid-row"><span>ID</span><strong>${cardEsc(c.line1||'NBR-0001')}</strong></div>
                <div class="cid-row"><span>Tier</span><strong>${cardEsc(c.line2||'Gold')}</strong></div>
                <div class="cid-row"><span>Valid</span><strong>${cardEsc(c.line3||'2026')}</strong></div>
                <div class="cid-barcode"></div>
            </div>`;
    } else if(type === 'referral'){
        el.className = 'card-render card-referral';
        el.innerHTML = `
            <div class="ci-deco">🌿</div><div class="ci-deco two">💚</div>
            <div class="ci-inner">
                <img class="ci-logo" src="${logo}" crossorigin="anonymous">
                <div class="ci-eyebrow">${cardEsc(c.title||'Refer & Earn')}</div>
                <h2 class="ci-title">${cardEsc(c.name||'A gift for you')}</h2>
                <p class="ref-offer">${cardEsc(c.line1||'10% off your first order')}</p>
                <div class="ref-code-wrap"><span>Use code</span><div class="ref-code">${cardEsc(c.line2||'CODE')}</div></div>
                ${c.line3?`<p class="ref-link">${cardEsc(c.line3)}</p>`:''}
                <div class="ci-brand">${cardEsc(c.brand||'Nature by Regina')}</div>
            </div>`;
    } else {
        el.className = 'card-render card-invite';
        el.innerHTML = `
            <div class="ci-deco">🌿</div><div class="ci-deco two">🍃</div>
            <div class="ci-inner">
                <img class="ci-logo" src="${logo}" crossorigin="anonymous">
                <div class="ci-eyebrow">${cardEsc(c.title||"You're Invited")}</div>
                <h2 class="ci-title">${cardEsc(c.name||'Our Event')}</h2>
                ${photo?`<div class="ci-photo"><img src="${photo}" crossorigin="anonymous"></div>`:''}
                <div class="ci-lines">
                    ${c.line1?`<div>📅 ${cardEsc(c.line1)}</div>`:''}
                    ${c.line2?`<div>📍 ${cardEsc(c.line2)}</div>`:''}
                    ${c.line3?`<div>⏰ ${cardEsc(c.line3)}</div>`:''}
                </div>
                ${c.message?`<p class="ci-msg">"${cardEsc(c.message)}"</p>`:''}
                <div class="ci-brand">${cardEsc(c.brand||'Nature by Regina')}</div>
            </div>`;
    }
}

function _snap(el){
    return html2canvas(el, {scale: 2, backgroundColor: null, useCORS: true, logging: false});
}
function cardDownloadPNG(el, name){
    _snap(el).then(canvas => {
        canvas.toBlob(b => {
            const a = document.createElement('a');
            a.href = URL.createObjectURL(b); a.download = (name||'card') + '.png'; a.click();
            setTimeout(()=>URL.revokeObjectURL(a.href), 2000);
        });
    });
}
function cardDownloadPDF(el, name){
    _snap(el).then(canvas => {
        const img = canvas.toDataURL('image/png');
        const w = canvas.width, h = canvas.height;
        const { jsPDF } = window.jspdf;
        const pdf = new jsPDF({ orientation: w > h ? 'landscape' : 'portrait', unit: 'px', format: [w, h] });
        pdf.addImage(img, 'PNG', 0, 0, w, h);
        pdf.save((name||'card') + '.pdf');
    });
}
