from flask import Flask, request, send_file
from PIL import Image, ImageOps
import requests
from io import BytesIO
import config

app = Flask(__name__)

def pixelate_image(image, pixel_size):
    small = image.resize(
        (image.size[0] // pixel_size, image.size[1] // pixel_size), resample=Image.BILINEAR
    )
    result = small.resize(image.size, Image.NEAREST)
    return result

def apply_sepia(image):
    sepia_image = ImageOps.colorize(ImageOps.grayscale(image), '#704214', '#C0C0C0')
    return sepia_image


def apply_internal_filters(image, filters):
    for filter_name, filter_param in filters.items():
        print(filter_name, filter_param)
        if filter_name == 'pixel':
            try:
                pixel_size = int(filter_param)
                image = pixelate_image(image, pixel_size)
            except ValueError:
                raise ValueError("Invalid pixelate parameter")
        elif filter_name == 'filter' and filter_param == 'sepia':
            image = apply_sepia(image)
    return image

@app.route('/cat', methods=['GET'])
@app.route('/cat/<path:path>', methods=['GET'])
def cat(path=None):
    base_url = config.BASE_URL
    query_params = {}
    internal_filters = {}

    if path is not None:
        if path.startswith('says'):
            _, text = path.split('/', 1)
            base_url = f"{base_url}/says/{text}"

    for key, value in request.args.items():
        if key in config.INTERNAL_FILTERS or value in config.INTERNAL_FILTERS:
            internal_filters[key] = value
        else:
            external_value = config.FILTER_RENAME_MAP.get(value, value)
            query_params[key] = external_value

    print(query_params.items())
    query_string = "&".join([f"{key}={value}" for key, value in query_params.items()])
    image_url = f"{base_url}?{query_string}" if query_params else base_url

    response = requests.get(image_url)
    print(image_url)
    if response.status_code != 200:
        return "Error fetching the image", response.status_code

    image = Image.open(BytesIO(response.content))

    try:
        image = apply_internal_filters(image, internal_filters)
    except ValueError as e:
        return str(e), 400

    img_format = image.format or 'JPEG'

    img_io = BytesIO()
    image.save(img_io, format=img_format)
    img_io.seek(0)

    return send_file(img_io, mimetype=f'image/{img_format.lower()}')

if __name__ == '__main__':
    app.run(debug=True)