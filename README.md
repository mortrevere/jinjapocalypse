# Jinjapocalypse \o/

I hope you like jinja as much as I do

## Usage 

`docker run --rm -u $(id -u):$(id -g) -v $(pwd):/jinjapocalypse jinjapocalypse`

in a cwd like: 
```
.
├── build
├── media
└── src
```

- `src` is rendered under `build` following Jinjapocalypse conventions
- `media` is copied under `build/media`
- `build` contains the full output
- `src/lib.jinja` is included for all rendering contexts and not rendered to `build/`
- Post-rendering empty files are not included in `build` output
- It's jinja but with *hourris* and a fancy toolbox: `\o/` `/o/` `\o\` `_o_`


## Examples

### Including files

```jinja
\o/ src["header.html"] \o/
Hello world !
\o/ src["footer.html"] \o/
```

### Loading YAML files

```jinja
<section class="product-grid">
    /o/ for product in _o_["load_yaml"]("products.yaml") \o\
    \o/ product_item(product["image"], product["name"], product["price"]) \o/
    /o/ endfor \o\
</section>
```

### Defining macros

Use `src/lib.jinja`:

```
{% macro product_item(image, name, price) %}
<div class="product-item">
    <a href="{{ _o_["slugify"](name) }}.html">
    <img src="media/{{ image }}" alt="{{ name }}">
    </a>
    <div class="product-name">{{ name }}</div>
    <div class="product-price">{{ price }}€</div>
</div>
{% endmacro %}
```

Unfortunately, hourri-formatting is not available in `lib.jinja`.

### Dynamically creating files

```jinja
/o/ for product in _o_["load_yaml"]("products.yaml") \o\
\o/ _o_["start_page"](product["name"]) \o/
\o/ src["header.html"] \o/
<section class="product-page">
  <div class="product-info">
    <h2>\o/ product["name"] \o/</h2>
    ...
  </div>
</section>
\o/ src["footer.html"] \o/
\o/ _o_["end_page"]() \o/
/o/ endfor \o\
```
