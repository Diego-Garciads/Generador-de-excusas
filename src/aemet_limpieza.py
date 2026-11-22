import pandas as pd


COLUMNAS = ["idema", "ubi", "fint", "prec", "vmax", "vv", "ta"]

def limpiar(datos, ahora=None):

    df = pd.DataFrame(datos).reindex(columns=COLUMNAS) # Claude Opus 5.5 (bajo)
    df["fint"] = pd.to_datetime(df["fint"], utc=True)
    df["hora"] = df["fint"].dt.tz_convert("Europe/Madrid")
    df = df.drop_duplicates(subset=["idema", "fint"])

    ahora = ahora if ahora is not None else pd.Timestamp.now(tz="UTC")
    df["antiguedad_h"] = (ahora - df["fint"]).dt.total_seconds() / 3600

    return df.sort_values(["idema", "fint"]).reset_index(drop=True)
