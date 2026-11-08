"""Shop pages: product list, product pages with an order form, and the terms page.

Products live in content/shop/*.json, shop settings in content/shop.json.
While "checkout_live" is off, the order button opens an email with the order
details. When it is on, the order goes to /api/order, which creates a payment
page at morning (Green Invoice) and sends the buyer there.
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).parent

TXT = {
    "en": dict(shop="Shop", from_="From", size="Size", frame="Add a frame", frame_h="Frame", color="Frame color", delivery="Delivery",
               free="free", details="Your details", name="Full name", email="Email", phone="Phone",
               street="Street and number", city="City", notes="Notes (optional)", total="Total",
               pay="Order and pay", send="Send order", terms="Terms of sale", agree="I have read and agree to the",
               secure="Payment is made on a secure page of morning (Green Invoice). Card details never pass through this site.",
               manual="Your email app will open with the order details. I will reply with a payment link.",
               err="Something went wrong. Please try again, or email me.", wait="One moment…",
               back="All products", subject="Order: "),
    "he": dict(shop="חנות", from_="החל מ־", size="גודל", frame="הוספת מסגרת", frame_h="מסגרת", color="צבע המסגרת", delivery="משלוח",
               free="ללא עלות", details="פרטים להזמנה", name="שם מלא", email="דוא״ל", phone="טלפון",
               street="רחוב ומספר בית", city="עיר", notes="הערות (לא חובה)", total="סה״כ",
               pay="להזמנה ולתשלום", send="שליחת הזמנה", terms="תקנון האתר", agree="קראתי ואני מסכים/ה ל",
               secure="התשלום מתבצע בדף מאובטח של מורנינג (חשבונית ירוקה). פרטי האשראי לא עוברים באתר.",
               manual="תיפתח הודעת דוא״ל עם פרטי ההזמנה. אחזור אליך עם קישור לתשלום.",
               err="משהו השתבש. נסו שוב, או כתבו לי בדוא״ל.", wait="רגע…",
               back="כל המוצרים", subject="הזמנה: "),
}


def slugify(name):
    s = re.sub(r"[^\w֐-׿-]+", "-", name.lower()).strip("-")
    return s or "product"


def load_shop():
    f = ROOT / "content/shop.json"
    settings = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    products = []
    for f in sorted((ROOT / "content/shop").glob("*.json")) if (ROOT / "content/shop").exists() else []:
        p = json.loads(f.read_text(encoding="utf-8"))
        if p.get("draft") or not p.get("variants"):
            continue
        p["slug"] = slugify(f.stem)
        products.append(p)
    products.sort(key=lambda p: (p.get("order") or 999, p["slug"]))
    return settings, products


def money(n, cur, lng):
    n = int(n) if float(n).is_integer() else n
    return f"{n} {cur}" if lng == "he" else f"{cur}{n}"


def render(lng, site, settings, products, out, page, pic, paras, e, CARD, TILE):
    SHOP_CARD = "(max-width:560px) 100vw, (max-width:900px) 50vw, 33vw"
    x, cur = TXT[lng], settings.get("currency") or "₪"
    t = lambda p, k: p.get(f"{k}_{lng}") or p.get(f"{k}_en") or ""
    (out / "shop").mkdir(parents=True, exist_ok=True)

    # ---- product list ----
    cards = []
    for p in products:
        low = min([v.get("price") or 0 for v in p["variants"] if v.get("available", True) is not False] or [0])
        cover = p.get("cover") or (p.get("images") or [""])[0]
        fig = pic(cover, "", t(p, "title"), SHOP_CARD) if cover else ""
        blurb = re.split(r"\n\s*\n", t(p, "text").strip())[0] if t(p, "text") else ""
        cards.append(f'<a class="pcard" href="shop/{p["slug"]}.html">'
                     f'<div class="pcard-label"><h2>{e(t(p, "title"))}</h2><span class="price-from">{e(x["from_"])}{e(money(low, cur, lng))}</span></div>'
                     f'<div class="pframe">{fig}<div class="pcard-hover"><p>{e(blurb)}</p></div></div></a>')
    intro = settings.get(f"intro_{lng}")
    body = f'<section class="page-head"><h1>{e(x["shop"])}</h1>{paras(intro) if intro else ""}</section>\n' \
           f'<section class="grid shop-grid">\n' + "\n".join(cards) + "\n</section>"
    (out / "shop.html").write_text(page(lng, site, "shop.html", f"{x['shop']} · {site[f'name_{lng}']}", body, "shop.html"), encoding="utf-8")

    # ---- product pages ----
    live = bool(settings.get("checkout_live"))
    ship = settings.get("shipping_price") or 0
    on = lambda o: o.get("available", True) is not False
    name = lambda o, k: o.get(f"{k}_{lng}") or o.get(f"{k}_en") or ""
    for p in products:
        variants = []
        for v in p["variants"]:
            if not on(v):
                continue
            frames = [{"name": name(fr, "name"), "color": fr.get("color") or "#cccccc", "price": fr.get("price") or 0}
                      for fr in (v.get("frames") or []) if on(fr) and name(fr, "name")]
            variants.append({"label": name(v, "size"), "price": v.get("price") or 0, "frames": frames})
        if not variants:
            continue
        data = {
            "slug": p["slug"], "lang": lng, "title": t(p, "title"), "cur": cur, "live": live,
            "email": site.get("email", ""), "ship": ship, "variants": variants,
            "txt": {k: x[k] for k in ("subject", "total", "frame", "color", "delivery", "err", "wait", "name", "email", "phone", "street", "city", "notes", "size")},
            "deliveryLabels": [t(settings, "pickup"), t(settings, "shipping")],
        }
        sizes = "".join(
            f'<label class="opt"><input type="radio" name="variant" value="{i}"{" checked" if i == 0 else ""} required>'
            f'<span>{e(v["label"])}</span><span class="opt-price">{e(money(v["price"], cur, lng))}</span></label>'
            for i, v in enumerate(variants))
        any_frame = any(v["frames"] for v in variants)
        frame = (f'<fieldset class="field" id="frame-field"><legend>{e(x["frame_h"])}</legend>'
                 f'<label class="opt"><input type="checkbox" name="frame" id="frame"><span>{e(x["frame"])}</span>'
                 f'<span class="opt-price" id="frame-price"></span></label>'
                 f'<div class="swatches" id="frame-colors" hidden><span class="swatch-legend">{e(x["color"])}</span>'
                 f'<div class="swatch-row" id="swatch-row"></div></div></fieldset>') if any_frame else ""
        delivery = (f'<fieldset class="field"><legend>{e(x["delivery"])}</legend>'
                    f'<label class="opt"><input type="radio" name="delivery" value="pickup" checked><span>{e(t(settings, "pickup"))}</span><span class="opt-price">{e(x["free"])}</span></label>'
                    f'<label class="opt"><input type="radio" name="delivery" value="ship"><span>{e(t(settings, "shipping"))}</span><span class="opt-price">+{e(money(ship, cur, lng))}</span></label>'
                    f'</fieldset>') if ship else ""
        inp = lambda n, lab, typ="text", req=True, auto="": (
            f'<label class="inp"><span>{e(lab)}</span><input type="{typ}" name="{n}" id="o-{n}"'
            f'{" required" if req else ""}{f" autocomplete={chr(34)}{auto}{chr(34)}" if auto else ""}></label>')
        form = f"""<form class="order" id="order" novalidate>
  <fieldset class="field"><legend>{e(x["size"])}</legend>{sizes}</fieldset>
  {frame}
  {delivery}
  <fieldset class="field"><legend>{e(x["details"])}</legend>
    {inp("name", x["name"], auto="name")}{inp("email", x["email"], "email", auto="email")}{inp("phone", x["phone"], "tel", auto="tel")}
    <div id="address" hidden>{inp("street", x["street"], auto="street-address")}{inp("city", x["city"], auto="address-level2")}</div>
    <label class="inp"><span>{e(x["notes"])}</span><textarea name="notes" id="o-notes" rows="2"></textarea></label>
  </fieldset>
  <label class="agree"><input type="checkbox" name="agree" id="o-agree" required><span>{e(x["agree"])}<a href="../terms.html" target="_blank">{e(x["terms"])}</a></span></label>
  <div class="total"><span>{e(x["total"])}</span><strong id="total"></strong></div>
  <button type="submit" class="buy" id="buy">{e(x["pay"] if live else x["send"])}</button>
  <p class="fine">{e(x["secure"] if live else x["manual"])}</p>
  <p class="form-error" id="form-error" role="alert" hidden></p>
</form>"""
        imgs = [i for i in [p.get("cover")] + (p.get("images") or []) if i]
        gallery = "".join(pic(i, "../", t(p, "title") if n == 0 else "", TILE, eager=(n == 0)) for n, i in enumerate(imgs))
        body = f"""<article class="product">
  <div class="product-media gallery">{gallery}</div>
  <div class="product-info">
    <h1>{e(t(p, "title"))}</h1>
    <div class="product-text">{paras(t(p, "text"))}</div>
    {form}
  </div>
</article>
<nav class="pager"><a href="../shop.html">{e(x["back"])}</a></nav>
<script type="application/json" id="product-data">{json.dumps(data, ensure_ascii=False).replace("</", "<\\/")}</script>
<script>{ORDER_JS}</script>"""
        path = f"shop/{p['slug']}.html"
        (out / path).write_text(page(lng, site, path, f"{t(p, 'title')} · {site[f'name_{lng}']}", body, "shop.html", 1), encoding="utf-8")

    # ---- terms ----
    terms = settings.get(f"terms_{lng}") or ""
    html_terms = []
    for block in re.split(r"\n\s*\n", terms.strip()):
        lines = block.strip().split("\n")
        if lines[0].startswith("## "):
            html_terms.append(f"<h2>{e(lines[0][3:])}</h2>")
            lines = lines[1:]
        if lines:
            html_terms.append("<p>" + "<br>".join(e(l) for l in lines) + "</p>")
    body = f'<section class="terms"><h1>{e(x["terms"])}</h1>{"".join(html_terms)}</section>'
    (out / "terms.html").write_text(page(lng, site, "terms.html", f"{x['terms']} · {site[f'name_{lng}']}", body), encoding="utf-8")


ORDER_JS = r"""
(function(){
  var D=JSON.parse(document.getElementById('product-data').textContent);
  var f=document.getElementById('order'),T=D.txt;
  var fmt=function(n){return D.lang==='he'?n+' '+D.cur:D.cur+n;};
  var frameBox=document.getElementById('frame'),frameField=document.getElementById('frame-field');
  var addr=document.getElementById('address'),err=document.getElementById('form-error');
  var row=document.getElementById('swatch-row'),shownFor=-1;
  function esc(t){var d=document.createElement('div');d.textContent=t;return d.innerHTML;}
  function drawFrames(vi){
    if(!row||shownFor===vi)return;var v=D.variants[vi],keep=+(f.querySelector('[name=frame_color]:checked')||{value:0}).value;
    if(keep>=v.frames.length)keep=0;
    row.innerHTML=v.frames.map(function(fr,i){return '<label class="swatch"><input type="radio" name="frame_color" value="'+i+'"'+(i===keep?' checked':'')+'>'+
      '<span class="chip" style="--chip:'+esc(fr.color)+'"></span><span>'+esc(fr.name)+'</span><span class="swatch-price">+'+esc(fmt(fr.price))+'</span></label>';}).join('');
    shownFor=vi;
  }
  function state(){
    var vi=+(f.querySelector('[name=variant]:checked')||{value:0}).value,v=D.variants[vi];
    var ship=(f.querySelector('[name=delivery]:checked')||{}).value==='ship';
    var has=v.frames.length>0,fr=null;
    if(frameField){
      frameField.hidden=!has;if(!has)frameBox.checked=false;drawFrames(vi);
      var on=has&&frameBox.checked;document.getElementById('frame-colors').hidden=!on;
      if(on){fr=v.frames[+(f.querySelector('[name=frame_color]:checked')||{value:0}).value]||v.frames[0];}
      var prices=v.frames.map(function(x){return x.price;}),lo=Math.min.apply(null,prices.length?prices:[0]);
      document.getElementById('frame-price').textContent=has?'+'+fmt(fr?fr.price:lo):'';
    }
    addr.hidden=!ship;addr.querySelectorAll('input').forEach(function(i){i.required=ship;});
    var total=v.price+(fr?fr.price:0)+(ship?D.ship:0);
    document.getElementById('total').textContent=fmt(total);
    return {variant:vi,frame:fr,frameIndex:fr?v.frames.indexOf(fr):null,ship:ship,total:total,v:v};
  }
  f.addEventListener('change',state);state();
  function val(n){var el=f.elements[n];return el?el.value.trim():'';}
  f.addEventListener('submit',function(ev){
    ev.preventDefault();err.hidden=true;
    if(!f.checkValidity()){f.reportValidity();return;}
    var s=state(),btn=document.getElementById('buy');
    var order={product:D.slug,lang:D.lang,variant:s.variant,frame:s.frameIndex,delivery:s.ship?'ship':'pickup',
      name:val('name'),email:val('email'),phone:val('phone'),street:val('street'),city:val('city'),notes:val('notes')};
    if(!D.live){
      var lines=[D.title,T.size+': '+s.v.label+' ('+fmt(s.v.price)+')'];
      if(s.frame)lines.push(T.frame+': '+s.frame.name+' (+'+fmt(s.frame.price)+')');
      lines.push(T.delivery+': '+D.deliveryLabels[s.ship?1:0]+(s.ship?' (+'+fmt(D.ship)+')':''));
      lines.push(T.total+': '+fmt(s.total),'',T.name+': '+order.name,T.email+': '+order.email,T.phone+': '+order.phone);
      if(s.ship)lines.push(T.street+': '+order.street,T.city+': '+order.city);
      if(order.notes)lines.push(T.notes+': '+order.notes);
      location.href='mailto:'+D.email+'?subject='+encodeURIComponent(T.subject+D.title)+'&body='+encodeURIComponent(lines.join('\n'));
      return;
    }
    var label=btn.textContent;btn.disabled=true;btn.textContent=T.wait;
    fetch('/api/order',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(order)})
      .then(function(r){return r.json().then(function(j){if(!r.ok||!j.url)throw 0;location.href=j.url;});})
      .catch(function(){err.textContent=T.err;err.hidden=false;btn.disabled=false;btn.textContent=label;});
  });
})();
"""
