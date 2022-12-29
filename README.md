# DataWarga

Data warga adalah aplikasi sumber terbuka (_open source_) web berbasis python Django web-framework yang dipergunakan untuk perekaman data warga ditingkat RT atau RW.

## Quick Start

Persiapan : 
- postgresql versi >= 14 ;  buat database e.g `datawarga`

```
cd /path/to/source/datawarga
python3 -m venv .venv
source .venv/bin/activate
pip install -Ur requirements.txt
```

Buat file `.env-dev.sh` yang isinya e.g :

```
export DATA_WARGA_SECRET="<isi dengan generated secret>"
export DB_HOST="localhost"
export DB_NAME="datawarga"
export DB_PASS="katasandi-postgres-anda"
export DB_PORT="5432"
export DB_USER="database-user-postgres-anda"
```

untuk DATA_WARGA_SECRET, dapat mengikuti [tutorial ini](https://www.educative.io/answers/how-to-generate-a-django-secretkey).

kemudian :
```
source .env.sh
cd datawarga
python manage.py migrate
python manage.py runserver 18000
```

Buka browser dan akses http://localhost:18000

## Production Deployment

Untuk melakukan deployment production, mohon ikuti best practice dari Django sendiri. Referesi : 
- https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/
- https://docs.djangoproject.com/en/4.1/howto/static-files/deployment/#serving-static-files-in-production
- https://www.freecodecamp.org/news/django-in-the-wild-tips-for-deployment-survival-9b491081c2e4/


## Kontribusi
Anda dapat berkontribusi dengan melakukan fork dan / atau mengajukan Pull Request. Jika ada bug atau sesuatu yang ingin diimprove, sila mengisi "Issue".
