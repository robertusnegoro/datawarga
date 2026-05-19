from __future__ import annotations
import random
import string
from datetime import date, datetime, timedelta
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from kependudukan.models import (
    Warga,
    Kompleks,
    TransaksiIuranBulanan,
    SummaryTransaksiBulanan,
    WargaPermissionGroup,
)
from kependudukan.management.commands.summarize_iuran_bulanan import summarize

INDONESIAN_MALE_NAMES: list[str] = [
    "Ahmad",
    "Budi",
    "Candra",
    "Dedi",
    "Eko",
    "Fajar",
    "Guntur",
    "Hendra",
    "Iwan",
    "Joko",
    "Kurniawan",
    "Lukman",
    "Mulyono",
    "Nugroho",
    "Oki",
    "Prabowo",
    "Rian",
    "Setyawan",
    "Taufik",
    "Umar",
    "Wahyu",
    "Yanto",
    "Andi",
    "Aditya",
    "Agung",
    "Agus",
    "Anwar",
    "Arif",
    "Bagus",
    "Bambang",
    "Denny",
    "Eka",
    "Farhan",
    "Hadi",
    "Hasan",
    "Indra",
    "Roni",
    "Slamet",
    "Rizky",
    "Teguh",
    "Hendri",
    "Faisal",
    "Dwi",
    "Tri",
    "Agus",
    "Asep",
]

INDONESIAN_FEMALE_NAMES: list[str] = [
    "Adinda",
    "Bunga",
    "Citra",
    "Dewi",
    "Eka",
    "Fitri",
    "Gita",
    "Hapsari",
    "Indah",
    "Julianti",
    "Kartika",
    "Laras",
    "Mega",
    "Ningsih",
    "Ony",
    "Putri",
    "Ratih",
    "Sari",
    "Tri",
    "Utami",
    "Wulan",
    "Yanti",
    "Amalia",
    "Anisa",
    "Aulia",
    "Dian",
    "Endah",
    "Ika",
    "Lia",
    "Maya",
    "Novita",
    "Rina",
    "Santi",
    "Sri",
    "Tari",
    "Windy",
    "Yuni",
    "Zahra",
    "Rini",
    "Ratna",
    "Siti",
    "Nur",
    "Karin",
    "Nabila",
    "Lestari",
    "Desi",
]

INDONESIAN_LAST_NAMES: list[str] = [
    "Saputra",
    "Wibowo",
    "Pratama",
    "Hidayat",
    "Kusuma",
    "Lestari",
    "Nugraha",
    "Sanjaya",
    "Setiawan",
    "Wijaya",
    "Siregar",
    "Nasution",
    "Ginting",
    "Simanjuntak",
    "Harahap",
    "Pasaribu",
    "Lubis",
    "Tanjung",
    "Pane",
    "Siahaan",
    "Gunawan",
    "Susanto",
    "Sutrisno",
    "Budiman",
    "Hartono",
    "Salim",
    "Purnama",
    "Subagyo",
    "Wahyudi",
    "Kurnia",
    "Haryanto",
    "Kurniawan",
    "Sitorus",
    "Sutanto",
    "Laksana",
    "Dharma",
    "Utomo",
]

INDONESIAN_CITIES: list[str] = [
    "Jakarta",
    "Bandung",
    "Surabaya",
    "Medan",
    "Semarang",
    "Yogyakarta",
    "Malang",
    "Makassar",
    "Denpasar",
    "Palembang",
    "Balikpapan",
    "Bogor",
    "Depok",
    "Tangerang",
    "Bekasi",
    "Solo",
    "Cirebon",
    "Pontianak",
    "Samarinda",
]


class Command(BaseCommand):
    help = "Generates realistic, heterogeneous dummy data for kependudukan models."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--total-kompleks",
            type=int,
            default=20,
            help="Total number of Kompleks (houses) to generate.",
        )
        parser.add_argument(
            "--occupancy-rate",
            type=float,
            default=0.8,
            help="Fraction of Kompleks that are occupied by residents (0.0 to 1.0).",
        )
        parser.add_argument(
            "--years",
            type=int,
            default=2,
            help="Number of years of transaction history to generate (must be >= 1).",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="Optional seed for the random number generator.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Deletes existing Kompleks, Warga, and TransaksiIuranBulanan data first.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        total_kompleks: int = options["total_kompleks"]
        occupancy_rate: float = options["occupancy_rate"]
        years: int = options["years"]
        seed: int | None = options["seed"]
        clear: bool = options["clear"]

        if seed is not None:
            random.seed(seed)

        if total_kompleks <= 0:
            self.stderr.write(
                self.style.ERROR("Total kompleks must be greater than 0.")
            )
            return
        if not (0.0 <= occupancy_rate <= 1.0):
            self.stderr.write(
                self.style.ERROR("Occupancy rate must be between 0.0 and 1.0.")
            )
            return
        if years <= 0:
            self.stderr.write(self.style.ERROR("Years must be greater than 0."))
            return

        # Check safety limits
        limit = getattr(settings, "GENERATE_KOMPLEKS_LIMIT", 200)
        if total_kompleks > limit:
            self.stderr.write(
                self.style.ERROR(
                    f"Total kompleks requested ({total_kompleks}) exceeds limit ({limit})."
                )
            )
            return

        self.stdout.write(
            f"Generating dummy data: complexes={total_kompleks}, occupancy={occupancy_rate:.1%}, years={years}, clear={clear}"
        )

        with transaction.atomic():
            if clear:
                self.stdout.write("Clearing existing data...")
                TransaksiIuranBulanan.objects.all().delete()
                SummaryTransaksiBulanan.objects.all().delete()
                Warga.objects.all().delete()
                Kompleks.objects.all().delete()
                self.stdout.write("Existing data cleared.")

            # Ensure permission group exists
            perm_group, _ = WargaPermissionGroup.objects.get_or_create(
                group_name="Warga Group"
            )

            # Generate Kompleks
            self.stdout.write("Generating Kompleks...")
            kompleks_list: list[Kompleks] = []

            blocks = ["A", "B", "C", "D", "E", "F", "G", "H"]
            rt_list = ["001", "002", "003", "004"]

            # Retrieve defaults from settings
            default_alamat = getattr(settings, "ALAMAT", "Jalan Nirwana")
            default_kecamatan = getattr(settings, "KECAMATAN", "SETU")
            default_kelurahan = getattr(settings, "KELURAHAN", "BABAKAN")
            default_kota = getattr(settings, "KOTA", "TANGERANG SELATAN")
            default_provinsi = getattr(settings, "PROVINSI", "BANTEN")
            default_rw = getattr(settings, "RUKUNWARGA", "012")

            generated_houses = set()

            for _ in range(total_kompleks):
                # Ensure unique block + number combination
                while True:
                    blok = random.choice(blocks)
                    nomor = str(random.randint(1, 30))
                    if (blok, nomor) not in generated_houses:
                        generated_houses.add((blok, nomor))
                        break

                kompleks = Kompleks.objects.create(
                    alamat=default_alamat,
                    kecamatan=default_kecamatan,
                    kelurahan=default_kelurahan,
                    kode_pos=(
                        "15315" if "TANGERANG" in default_kota.upper() else "10000"
                    ),
                    kota=default_kota,
                    provinsi=default_provinsi,
                    cluster=random.choice(
                        ["Griya Asri", "Green Valley", "Bukit Raya", None]
                    ),
                    blok=blok,
                    nomor=nomor,
                    rt=random.choice(rt_list),
                    rw=default_rw,
                    permission_group=perm_group,
                    description=f"Rumah di blok {blok} nomor {nomor}",
                )
                kompleks_list.append(kompleks)

            self.stdout.write(f"Generated {len(kompleks_list)} Kompleks records.")

            # Generate Warga
            self.stdout.write("Generating Warga...")
            used_niks: set[str] = set()
            warga_count = 0
            occupied_count = 0

            religions = ["ISLAM", "KRISTEN", "KATHOLIK", "HINDU", "BUDDHA", "KONGHUCU"]
            religion_weights = [0.85, 0.08, 0.04, 0.015, 0.01, 0.005]

            status_tinggal_choices = ["TETAP", "KONTRAK", "KOST", "PINDAH"]
            status_tinggal_weights = [0.75, 0.15, 0.07, 0.03]

            jobs = [
                "PNS",
                "KARYAWAN SWASTA",
                "KARYAWAN BUMN",
                "TNI",
                "POLRI",
                "NAKES",
                "WIRASWASTA",
                "MENGURUS RUMAH TANGGA",
                "GURU",
                "OJEK",
                "LAINNYA",
            ]

            for kompleks in kompleks_list:
                # Determine occupancy
                if random.random() > occupancy_rate:
                    continue

                occupied_count += 1
                family_size = random.randint(1, 5)
                no_kk = "3276" + "".join(random.choices(string.digits, k=12))

                # Define household characteristics
                household_religion = random.choices(
                    religions, weights=religion_weights, k=1
                )[0]
                household_status_tinggal = random.choices(
                    status_tinggal_choices, weights=status_tinggal_weights, k=1
                )[0]

                # Determine address KTP
                if household_status_tinggal == "TETAP":
                    alamat_ktp = f"{kompleks.alamat}, RT {kompleks.rt}/RW {kompleks.rw}, {kompleks.kelurahan}"
                else:
                    alamat_ktp = f"Jl. Pahlawan No. {random.randint(1, 100)}, {random.choice(INDONESIAN_CITIES)}"

                # Construct family roles
                family_roles: list[dict[str, Any]] = []

                # Head of family
                head_gender = random.choices(
                    ["LAKI-LAKI", "PEREMPUAN"], weights=[0.85, 0.15], k=1
                )[0]
                head_age = random.randint(30, 75)
                if head_gender == "LAKI-LAKI":
                    head_relation = "SUAMI"
                    head_status = random.choices(
                        ["KAWIN", "BELUM KAWIN", "CERAI HIDUP", "CERAI MATI"],
                        weights=[0.80, 0.05, 0.05, 0.10],
                        k=1,
                    )[0]
                else:
                    head_relation = random.choices(
                        ["ISTRI", "LAINNYA"], weights=[0.70, 0.30], k=1
                    )[0]
                    head_status = random.choices(
                        ["KAWIN", "BELUM KAWIN", "CERAI HIDUP", "CERAI MATI"],
                        weights=[0.50, 0.10, 0.20, 0.20],
                        k=1,
                    )[0]

                family_roles.append(
                    {
                        "kepala_keluarga": True,
                        "gender": head_gender,
                        "status_keluarga": head_relation,
                        "status": head_status,
                        "age": head_age,
                    }
                )

                # Spouse if married and family size > 1
                if family_size > 1 and head_status == "KAWIN":
                    spouse_gender = (
                        "PEREMPUAN" if head_gender == "LAKI-LAKI" else "LAKI-LAKI"
                    )
                    spouse_relation = (
                        "ISTRI" if spouse_gender == "PEREMPUAN" else "SUAMI"
                    )
                    spouse_age = max(18, head_age + random.randint(-5, 5))
                    family_roles.append(
                        {
                            "kepala_keluarga": False,
                            "gender": spouse_gender,
                            "status_keluarga": spouse_relation,
                            "status": "KAWIN",
                            "age": spouse_age,
                        }
                    )

                # Additional members (Children, Parents, Siblings)
                while len(family_roles) < family_size:
                    relation = random.choices(
                        ["ANAK", "ORANG TUA", "SAUDARA"],
                        weights=[0.80, 0.10, 0.10],
                        k=1,
                    )[0]

                    if relation == "ANAK":
                        child_gender = random.choice(["LAKI-LAKI", "PEREMPUAN"])
                        child_age = max(0, head_age - random.randint(20, 38))
                        child_status = "BELUM KAWIN"
                        if child_age >= 18:
                            child_status = random.choices(
                                ["BELUM KAWIN", "KAWIN"], weights=[0.85, 0.15], k=1
                            )[0]
                        family_roles.append(
                            {
                                "kepala_keluarga": False,
                                "gender": child_gender,
                                "status_keluarga": "ANAK",
                                "status": child_status,
                                "age": child_age,
                            }
                        )
                    elif relation == "ORANG TUA":
                        parent_gender = random.choice(["LAKI-LAKI", "PEREMPUAN"])
                        parent_age = head_age + random.randint(20, 35)
                        parent_status = random.choices(
                            ["KAWIN", "CERAI MATI", "CERAI HIDUP"],
                            weights=[0.40, 0.50, 0.10],
                            k=1,
                        )[0]
                        family_roles.append(
                            {
                                "kepala_keluarga": False,
                                "gender": parent_gender,
                                "status_keluarga": "ORANG TUA",
                                "status": parent_status,
                                "age": parent_age,
                            }
                        )
                    else:  # SAUDARA
                        sibling_gender = random.choice(["LAKI-LAKI", "PEREMPUAN"])
                        sibling_age = max(15, head_age + random.randint(-12, 12))
                        sibling_status = random.choices(
                            ["BELUM KAWIN", "KAWIN", "CERAI HIDUP"],
                            weights=[0.60, 0.30, 0.10],
                            k=1,
                        )[0]
                        family_roles.append(
                            {
                                "kepala_keluarga": False,
                                "gender": sibling_gender,
                                "status_keluarga": "SAUDARA",
                                "status": sibling_status,
                                "age": sibling_age,
                            }
                        )

                # Create Warga database records
                for role in family_roles:
                    # NIK generation with collision detection
                    while True:
                        nik = "3276" + "".join(random.choices(string.digits, k=12))
                        if (
                            nik not in used_niks
                            and not Warga.objects.filter(nik=nik).exists()
                        ):
                            used_niks.add(nik)
                            break

                    # Construct name
                    if role["gender"] == "LAKI-LAKI":
                        first_name = random.choice(INDONESIAN_MALE_NAMES)
                    else:
                        first_name = random.choice(INDONESIAN_FEMALE_NAMES)
                    last_name = random.choice(INDONESIAN_LAST_NAMES)
                    full_name = f"{first_name} {last_name}"

                    # Job assignment
                    age = role["age"]
                    if age < 6:
                        job = "LAINNYA"
                    elif age < 22:
                        job = "PELAJAR/MAHASISWA"
                    else:
                        if role["status_keluarga"] == "ISTRI" and random.random() < 0.4:
                            job = "MENGURUS RUMAH TANGGA"
                        else:
                            job = random.choice(jobs)

                    # Contact info
                    no_hp = (
                        "08"
                        + "".join(
                            random.choices(string.digits, k=random.randint(9, 10))
                        )
                        if age >= 12
                        else None
                    )
                    email = (
                        f"{first_name.lower()}.{last_name.lower()}@example.com"
                        if age >= 15
                        else None
                    )

                    # Birth Date
                    birth_year = date.today().year - age
                    # Choose a random day in the year
                    birth_date = date(birth_year, 1, 1) + timedelta(
                        days=random.randint(0, 364)
                    )

                    Warga.objects.create(
                        agama=household_religion,
                        email=email,
                        nama_lengkap=full_name,
                        nik=nik,
                        no_hp=no_hp,
                        no_kk=no_kk,
                        pekerjaan=job,
                        status=role["status"],
                        tanggal_lahir=birth_date,
                        tempat_lahir=random.choice(INDONESIAN_CITIES),
                        jenis_kelamin=role["gender"],
                        kewarganegaraan="Indonesia/WNI",
                        status_tinggal=household_status_tinggal,
                        status_keluarga=role["status_keluarga"],
                        alamat_ktp=alamat_ktp,
                        kompleks=kompleks,
                        kepala_keluarga=role["kepala_keluarga"],
                    )
                    warga_count += 1

            self.stdout.write(
                f"Generated {warga_count} Warga records in {occupied_count} occupied complexes."
            )

            # Generate Transactions (TransaksiIuranBulanan)
            self.stdout.write("Generating TransaksiIuranBulanan...")
            current_date = date.today()
            default_iuran = getattr(settings, "IURAN_BULANAN", 150000)

            years_to_generate = range(
                current_date.year - years + 1, current_date.year + 1
            )
            tx_count = 0

            # Only generate iuran transactions for occupied houses
            occupied_kompleks = [
                k for k in kompleks_list if Warga.objects.filter(kompleks=k).exists()
            ]

            for kompleks in occupied_kompleks:
                for year in years_to_generate:
                    # Determine monthly periods to generate
                    max_month = current_date.month if year == current_date.year else 12

                    for month in range(1, max_month + 1):
                        # Heterogeneous behavior: 85% probability of payment
                        if random.random() > 0.85:
                            continue

                        # Create iuran
                        tx = TransaksiIuranBulanan.objects.create(
                            kompleks=kompleks,
                            keterangan=f"Iuran otomatis generator bulan {month} tahun {year}",
                            periode_bulan=month,
                            periode_tahun=year,
                            total_bayar=default_iuran,
                        )

                        # Set simulated past tanggal_bayar to bypass auto_now_add
                        simulated_date = date(year, month, random.randint(1, 15))
                        # In case the simulated date is in the future, cap it to today
                        if simulated_date > current_date:
                            simulated_date = current_date

                        TransaksiIuranBulanan.objects.filter(pk=tx.pk).update(
                            tanggal_bayar=simulated_date
                        )
                        tx_count += 1

            self.stdout.write(f"Generated {tx_count} payment transactions.")

            # Call the shared summarize command for each generated year and block
            self.stdout.write("Summarizing transactions using shared logic...")
            generated_bloks = set(k.blok for k in kompleks_list)
            for year in years_to_generate:
                for blok in generated_bloks:
                    summarize(year, blok)

            self.stdout.write(self.style.SUCCESS("Successfully generated dummy data!"))
