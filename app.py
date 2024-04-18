# app.py
from flask import Flask, request, render_template, jsonify
import pandas as pd
from geopy.geocoders import ArcGIS, Nominatim
from geopy.exc import GeocoderTimedOut, GeopyError
from flask import Response

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    if file:
        df = pd.read_csv(file)
        return jsonify(columns=list(df.columns))
    return jsonify({'error': 'No file provided'}), 400

@app.route('/geolocalizar', methods=['POST'])
@app.route('/geolocalizar', methods=['POST'])
def geolocalizar():
    selected_columns = request.form.getlist('columns')
    file = request.files['file']
    if file:
        df = pd.read_csv(file)
        # Construir la dirección completa basada en las columnas seleccionadas
        df['direccion_formada'] = df.apply(lambda row: ' '.join(str(row[col]) for col in selected_columns if col in row), axis=1)
        # Asegúrate de que 'nombre_completo' es una de las columnas en tu CSV
        if 'nombre_completo' not in df.columns:
            return jsonify({'error': "'nombre_completo' column is missing in the CSV file"}), 400
        
        # Prepara una lista para almacenar los resultados de geolocalización
        resultados = []
        for _, row in df.iterrows():
            # Obtiene la latitud y longitud de la dirección formada
            lat, lng = geolocalizar_direccion(row['direccion_formada'])
            # Añade los datos de geolocalización y el nombre completo al resultado
            resultados.append({
                'nombre_completo': row['nombre_completo'],
                'direccion': row['direccion_formada'],
                'latitud': lat, 
                'longitud': lng
            })
        
        # Convierte los resultados en un JSON para la respuesta
        return jsonify(resultados)
    
    # Manejo de error si no se proporciona archivo
    return jsonify({'error': 'No file provided'}), 400

def geolocalizar_direccion(direccion):
    arcgis_geolocator = ArcGIS(user_agent='my_app')
    osm_geolocator = Nominatim(user_agent='my_app')

    try:
        location_arcgis = arcgis_geolocator.geocode(direccion, timeout=10)
        if location_arcgis:
            return location_arcgis.latitude, location_arcgis.longitude
        
        location_osm = osm_geolocator.geocode(direccion, timeout=10)
        if location_osm:
            return location_osm.latitude, location_osm.longitude

        return None, None
    except (GeocoderTimedOut, GeopyError, Exception) as e:
        print(f'Error al geolocalizar: {str(e)}')
        return None, None

@app.route('/exportar', methods=['POST'])
def exportar():
    try:
        datos = request.json.get('datos', [])
        if not datos:
            return jsonify({'error': 'No data provided'}), 400
        
        # Crear un DataFrame de los datos
        df = pd.DataFrame(datos)

        if 'bounds' in request.json:
            bounds = request.json['bounds']
            df = df[(df['latitud'] >= bounds['south']) &
                    (df['latitud'] <= bounds['north']) &
                    (df['longitud'] >= bounds['west']) &
                    (df['longitud'] <= bounds['east'])]

        csv_string = df.to_csv(index=False)
        return Response(
            csv_string,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=datos_geolocalizados.csv"})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def esta_dentro(dato, bounds):
    lat, lng = float(dato['latitud']), float(dato['longitud'])
    return (bounds['south'] <= lat <= bounds['north']) and (bounds['west'] <= lng <= bounds['east'])

if __name__ == '__main__':
    app.run(debug=True)
