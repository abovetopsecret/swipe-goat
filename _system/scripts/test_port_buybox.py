"""python3 test_port_buybox.py: the buybox matcher must wire the price, not the row around it."""
from types import SimpleNamespace
from port import wire_shopify_buybox

PAGE = """<div class="buy">
<div class="p__price-row"><span class="p__price">$39.98</span><span class="p__compare-price">$44.99</span><span>Save 11%</span></div>
<div class="p__quantity"><input type="number" value="1"></div>
<button class="p__add-button" type="button">Add to cart</button>
</div>"""

out, _ = wire_shopify_buybox(PAGE, SimpleNamespace())
row = out[out.index('p__price-row'):out.index('p__quantity')]
assert "product.price" in row and "product.compare_at_price" in row, row
assert "Save 11%" in row, "the row was overwritten, not the price inside it"

# JSON-LD is data: it must stay in the markup, never be glued into the page JS.
from ghl_export import split_blocks
js, rest = split_blocks('<script type="application/ld+json">{"a":1}</script><script>var x=1</script>', "script")
assert js == ["var x=1"], js
assert 'ld+json' in rest, rest
print("ok")
