import os
import tempfile

from google.cloud import storage, vision
from wand.image import Image

storage_client = storage.Client()
vision_client = vision.ImageAnnotatorClient()

# Si el contenido es explicito le aplica un filtro Blur a la imagen

def blur_offensive_images(data, context):
    file_data = data

    file_name = file_data['name']
    bucket_name = file_data['bucket']

    blob = storage_client.bucket(bucket_name).get_blob(file_name)
    blob_uri = f'gs://{bucket_name}/{file_name}'
    blob_source = {'source': {'image_uri': blob_uri}}

    # Se descartan las imagenes que ya fueron procesadas
    if blob.metadata and blob.metadata['status'] == 'blurred':
        print(f'La imagen {file_name} ya tiene el filtro blur')
        return

    print(f'Se esta analizando la imagen: {file_name}')

    result = vision_client.safe_search_detection(blob_source)  #Instancia del metodo detection
    detected = result.safe_search_annotation

    if detected.adult ==5 or detected.violence ==5:
        print(f'La imagen {file_name} fue considerada como inadecuada')
        return __blur_image(blob, bucket_name)
    else:
        print(f'La imagen {file_name} es adecuada')


def __blur_image(current_blob, bucket_name):
    file_name = current_blob.name
    _, temp_local_filename = tempfile.mkstemp()
    content_type = current_blob.content_type
    current_blob.download_to_filename(temp_local_filename)

    with Image(filename=temp_local_filename) as image:
        image.resize(*image.size, blur=16, filter='hamming')
        image.save(filename=temp_local_filename)

    print(f'A la imagen {file_name} se le aplico el filtro blur')

    blur_bucket = storage_client.bucket(bucket_name)
    new_blob = blur_bucket.blob(file_name)
    new_blob.metadata = {'status':'blurred'}
    new_blob.upload_from_filename(temp_local_filename, content_type=content_type)
    new_blob.make_public()
    print(f'La nueva imagen fue subida a: gs://{bucket_name}/{file_name}')

    os.remove(temp_local_filename)