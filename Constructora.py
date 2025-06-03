import os
import pickle
import datetime
import math
import matplotlib.pyplot as plt

# ---------------------------------------------------------
#  CONSTANTES Y CONFIGURACION GLOBAL
# ---------------------------------------------------------
# TASA_DE_CONVERSION: 1 USD = 4000 COP, 1 EUR = 4300 COP
TASA_DE_CONVERSION = {
    "COP": 1.0,
    "USD": 1 / 4000.0,
    "EUR": 1 / 4300.0
}
SIMBOLO_MONEDA = {
    "COP": "$",
    "USD": "$",
    "EUR": "€"
}
# Moneda por defecto
moneda_actual = "COP"


def formatear_valor(valor_cop):
    """
    Convierte un monto en COP a la moneda actual y devuelve
    un string con simbolo y codigo. Ejemplo:
    si valor_cop = 10000 y moneda_actual = "USD", retorna "$ 2.50 USD"
    """
    factor = TASA_DE_CONVERSION.get(moneda_actual, 1.0)
    convertido = valor_cop * factor
    simbolo = SIMBOLO_MONEDA.get(moneda_actual, "$")
    return f"{simbolo} {convertido:,.2f} {moneda_actual}"


# ---------------------------------------------------------
#  CLASE PRINCIPAL: Proyecto
# ---------------------------------------------------------
class Proyecto:
    def __init__(
        self,
        pid,
        tipo,
        fecha_inicio,
        direccion,
        area_lote,
        precio_terreno_m2,
        tamano,
        estrato,
        habitaciones,
        fecha_estimada_final
    ):
        # Datos basicos del proyecto
        self.pid = pid
        self.tipo = tipo           # "casas", "edificio" o "otro"
        self.fecha_inicio = fecha_inicio
        self.direccion = direccion
        self.area_lote = area_lote
        self.precio_terreno_m2 = precio_terreno_m2
        self.tamano = tamano       # "grande", "mediana" o "chica"
        self.estrato = estrato
        # Cantidad de habitaciones solo para "casas" o "edificio"
        self.habitaciones = habitaciones
        self.fecha_estimada_final = fecha_estimada_final

        # Zonas sociales en funcion del estrato
        if estrato >= 5:
            self.zonas_sociales = ["Piscina", "Sauna", "Gimnasio"]
        elif estrato == 4:
            self.zonas_sociales = ["Piscina", "Salon comun"]
        elif estrato == 3:
            self.zonas_sociales = ["Parque infantil", "Salon comun"]
        else:
            self.zonas_sociales = ["Zonas verdes", "Parque infantil"]

        # Porcentaje fijo de construccion segun tamano
        if tamano == "grande":
            self.porc_construccion = 80.0
        elif tamano == "mediana":
            self.porc_construccion = 60.0
        else:  # "chica"
            self.porc_construccion = 45.0

        # Indicadores de estado de finalizacion
        self.finalizado = False
        self.fecha_real_final = None

        # Calcular todos los valores derivados
        self._recalcular()

    def _recalcular(self):
        """
        Recalcula todos los atributos de area, costo, ganancia, precio, etc.
        Tambien aplica derivada para optimizar numero de unidades.
        """

        # 1) Area construida y area no construida (resto)
        self.area_construida = self.area_lote * (self.porc_construccion / 100.0)
        self.area_no_construida = self.area_lote - self.area_construida

        # 2) Calculo de area minima por unidad y numero de unidades segun tipo
        if self.tipo == "casas":
            # AREA MINIMA POR CASA segun tamano
            if self.tamano == "grande":
                # Casas grandes: 30 m2 por habitacion + 40 m2 sala-comedor
                self.area_min_vivienda = self.habitaciones * 30.0 + 40.0
            elif self.tamano == "mediana":
                # Casas medianas: 25 m2 por habitacion + 35 m2 sala-comedor
                self.area_min_vivienda = self.habitaciones * 25.0 + 35.0
            else:
                # Casas chiquas: area minima fija de 60 m2
                self.area_min_vivienda = 60.0

            # 2.1) Calculo costo terreno y construccion para hallar precio_base_m2
            costo_terreno = self.area_lote * self.precio_terreno_m2
            # Costo de construccion por m2 segun estrato (valores medios)
            if self.estrato == 3:
                costo_m2 = (1800000 + 2300000) / 2
            elif self.estrato == 4:
                costo_m2 = (2300000 + 2800000) / 2
            elif self.estrato == 5:
                costo_m2 = (2800000 + 3600000) / 2
            else:  # estrato 6 o mayor
                costo_m2 = (3600000 + 4500000) / 2

            costo_construccion = self.area_construida * costo_m2
            presupuesto_sin_ganancia = costo_terreno + costo_construccion

            # precio_base_m2 es el precio de venta sin contar penalizacion
            if self.area_construida > 0:
                # Multiplicamos por 1.20 porque la ganancia es del 20%
                precio_base_m2 = (1.20 * presupuesto_sin_ganancia) / self.area_construida
            else:
                precio_base_m2 = 0.0

            # 2.2) Definimos beta (penalizacion por cada casa extra)
            beta_casas = 50000.0  # COP de penalizacion

            # 2.3) Modelo de ingreso R(n) = n * area_min_vivienda * (precio_base_m2 - beta_casas * n)
            # Para maximizar R, igualamos derivada a cero:
            #   dR/dn = area_min_vivienda * (precio_base_m2 - 2 * beta_casas * n) = 0
            #   => precio_base_m2 - 2*beta_casas*n = 0
            #   => n_opt = precio_base_m2 / (2 * beta_casas)
            n_opt = precio_base_m2 / (2.0 * beta_casas)
            n_opt = max(1, math.floor(n_opt))  # por lo menos 1 unidad

            # 2.4) No superar la capacidad de area disponible
            capacidad_area = math.floor(self.area_construida / self.area_min_vivienda)
            if n_opt > capacidad_area:
                n_opt = capacidad_area

            self.num_viviendas = n_opt

        elif self.tipo == "edificio":
            # AREA MINIMA POR APARTAMENTO: 20 m2 por habitacion + 30 m2 sala-comedor
            self.area_min_vivienda = self.habitaciones * 20.0 + 30.0

            # 2.1) Calculo costo terreno y construccion
            costo_terreno = self.area_lote * self.precio_terreno_m2
            if self.estrato == 3:
                costo_m2 = (1800000 + 2300000) / 2
            elif self.estrato == 4:
                costo_m2 = (2300000 + 2800000) / 2
            elif self.estrato == 5:
                costo_m2 = (2800000 + 3600000) / 2
            else:
                costo_m2 = (3600000 + 4500000) / 2

            costo_construccion = self.area_construida * costo_m2
            presupuesto_sin_ganancia = costo_terreno + costo_construccion

            if self.area_construida > 0:
                precio_base_m2 = (1.20 * presupuesto_sin_ganancia) / self.area_construida
            else:
                precio_base_m2 = 0.0

            # 2.2) Definimos beta para edificios (penalizacion por cada apto extra)
            beta_edificio = 80000.0  # COP de penalizacion

            # 2.3) Igualamos derivada a cero:
            #   dR/dn = area_min_vivienda * (precio_base_m2 - 2 * beta_edificio * n) = 0
            n_opt = precio_base_m2 / (2.0 * beta_edificio)
            n_opt = max(1, math.floor(n_opt))

            # 2.4) No superar la capacidad de area
            capacidad_area = math.floor(self.area_construida / self.area_min_vivienda)
            if n_opt > capacidad_area:
                n_opt = capacidad_area

            self.num_viviendas = n_opt

            # 2.5) Distribuir en torres y aptos por torre fijos
            aptos_por_torre = 10
            num_torres = math.ceil(self.num_viviendas / aptos_por_torre)
            self.aptos_por_torre = min(aptos_por_torre, self.num_viviendas)
            self.num_torres = num_torres

        else:
            # Para tipo "otro", usamos 70% del lote en bodegas
            self.area_bodegas = self.area_lote * 0.70
            self.area_min_vivienda = 100.0  # m2 minimo por bodega
            self.num_viviendas = max(1, math.floor(self.area_bodegas / self.area_min_vivienda))

        # 3) Costo de terreno total (COP)
        self.costo_terreno_total = self.area_lote * self.precio_terreno_m2

        # 4) Costo construccion m2 segun estrato (valores medios)
        if self.estrato == 3:
            self.costo_construccion_m2 = (1800000 + 2300000) / 2
        elif self.estrato == 4:
            self.costo_construccion_m2 = (2300000 + 2800000) / 2
        elif self.estrato == 5:
            self.costo_construccion_m2 = (2800000 + 3600000) / 2
        else:
            self.costo_construccion_m2 = (3600000 + 4500000) / 2

        # 5) Costo de construccion total (COP)
        self.costo_construccion_total = self.area_construida * self.costo_construccion_m2

        # 6) Presupuesto total (terreno + construccion)
        self.presupuesto_total = self.costo_terreno_total + self.costo_construccion_total

        # 7) Ganancia deseada: 20% sobre presupuesto
        self.ganancia = self.presupuesto_total * 0.20

        # 8) Precio de venta por m2 (derivado sin penalizacion)
        if self.area_construida > 0:
            self.precio_venta_m2 = (1.20 * self.presupuesto_total) / self.area_construida
        else:
            self.precio_venta_m2 = 0.0

        # 9) Precio de venta total
        self.precio_venta_total = self.area_construida * self.precio_venta_m2

        # 10) Valor de cada unidad (en COP)
        if self.num_viviendas > 0:
            self.valor_casa = self.precio_venta_total / self.num_viviendas
        else:
            self.valor_casa = 0.0

    def calcular_derivada_valor_por_vivienda(self):
        """
        Calcula d(valor_por_unidad)/dn en el modelo de penalizacion:
        Se asume: valor_unidad = area_min_vivienda * (precio_base_m2 - beta * n)
        => derivada respecto a n: -beta * area_min_vivienda
        """
        if self.tipo == "casas":
            beta = 50000.0
        elif self.tipo == "edificio":
            beta = 80000.0
        else:
            return None
        return -beta * self.area_min_vivienda

    def duracion_estimada(self):
        """
        Retorna la duracion en dias entre fecha_estimada_final y fecha_inicio
        """
        return (self.fecha_estimada_final - self.fecha_inicio).days


# ---------------------------------------------------------
#  CLASE: BaseDeDatos para guardar proyectos con pickle
# ---------------------------------------------------------
class BaseDeDatos:
    def __init__(self, archivo="ProyectosGuardados.pkl"):
        self.archivo = archivo
        self.proyectos = self._cargar()

    def _cargar(self):
        """
        Carga el diccionario de proyectos desde un archivo pickle si existe,
        o devuelve un diccionario vacio en caso contrario.
        """
        if os.path.exists(self.archivo):
            with open(self.archivo, "rb") as f:
                try:
                    return pickle.load(f)
                except:
                    return {}
        return {}

    def _guardar(self):
        """
        Guarda el diccionario de proyectos en un archivo pickle.
        """
        with open(self.archivo, "wb") as f:
            pickle.dump(self.proyectos, f)

    def agregar(self, proyecto):
        """
        Agrega o actualiza un proyecto en la base de datos y guarda en disco.
        """
        self.proyectos[proyecto.pid] = proyecto
        self._guardar()

    def eliminar(self, pid):
        """
        Elimina un proyecto de la base de datos por su ID y actualiza el archivo.
        """
        if pid in self.proyectos:
            del self.proyectos[pid]
            self._guardar()

    def obtener(self, pid):
        """
        Retorna el proyecto con ID pid, o None si no existe.
        """
        return self.proyectos.get(pid)

    def listar(self):
        """
        Retorna una lista con todos los proyectos guardados.
        """
        return list(self.proyectos.values())


# ---------------------------------------------------------
#  FUNCIONES AUXILIARES DE ARCHIVOS Y RECIBOS
# ---------------------------------------------------------
def crear_carpetas():
    """
    Crea las carpetas 'Proyectos' y 'ProyectosFinalizados' si no existen.
    """
    os.makedirs("Proyectos", exist_ok=True)
    os.makedirs("ProyectosFinalizados", exist_ok=True)


def generar_recibo(proy):
    """
    Genera un archivo de texto en 'Proyectos/{pid}.txt' con los datos del proyecto,
    usando la moneda actual para formatear valores.
    """
    ruta = os.path.join("Proyectos", f"{proy.pid}.txt")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("===========================================\n")
        f.write("             RECIBO DE PROYECTO            \n")
        f.write("===========================================\n\n")

        f.write("1. DATOS GENERALES\n")
        f.write(f"   ID                         : {proy.pid}\n")
        f.write(f"   Tipo de Proyecto           : {proy.tipo.capitalize()}\n")
        f.write(f"   Fecha de Inicio            : {proy.fecha_inicio}\n")
        f.write(f"   Direccion                  : {proy.direccion}\n\n")

        f.write("2. AREAS Y TERRENO\n")
        f.write(f"   Area total del lote         : {proy.area_lote:,.2f} m2\n")
        f.write(f"   Precio terreno por m2       : {formatear_valor(proy.precio_terreno_m2)} /m2\n")
        f.write(f"   Costo terreno total         : {formatear_valor(proy.costo_terreno_total)}\n")
        f.write(f"   % Area construida           : {proy.porc_construccion:.0f} %\n")
        f.write(f"   Area construida             : {proy.area_construida:,.2f} m2\n")
        f.write(f"   Area no construida          : {proy.area_no_construida:,.2f} m2\n\n")

        f.write("3. RESTRICCIONES Y VIVIENDAS\n")
        if proy.tipo == "edificio":
            f.write(f"   Numero de torres            : {proy.num_torres}\n")
            f.write(f"   Aptos por torre             : {proy.aptos_por_torre}\n")
        f.write(f"   Habitaciones por unidad     : {proy.habitaciones}\n")
        f.write(f"   Area minima por unidad      : {proy.area_min_vivienda:,.2f} m2\n")
        f.write(f"   Numero de unidades estimado : {proy.num_viviendas:,d}\n")
        f.write(f"   Valor por unidad            : {formatear_valor(proy.valor_casa)}\n\n")

        f.write("4. COSTOS Y GANANCIAS\n")
        f.write(f"   Costo construccion por m2          : {formatear_valor(proy.costo_construccion_m2)} /m2\n")
        f.write(f"   Costo construccion total           : {formatear_valor(proy.costo_construccion_total)}\n")
        f.write(f"   Presupuesto (terreno+construccion) : {formatear_valor(proy.presupuesto_total)}\n")
        f.write(f"   Ganancia (20%)                     : {formatear_valor(proy.ganancia)}\n")
        f.write(f"   Precio venta por m2 (derivado)     : {formatear_valor(proy.precio_venta_m2)} /m2\n")
        f.write(f"   Precio venta total                 : {formatear_valor(proy.precio_venta_total)}\n\n")

        if proy.tipo in ["casas", "edificio"]:
            derivada = proy.calcular_derivada_valor_por_vivienda()
            if derivada is not None:
                f.write(f"   Derivada valor por unidad respecto num unidades: {derivada:,.2f}\n\n")

        f.write("5. ZONAS SOCIALES\n")
        f.write(f"   {', '.join(proy.zonas_sociales)}\n\n")

        f.write("6. FECHAS DE FINALIZACION\n")
        f.write(f"   Fecha estimada de finalizacion : {proy.fecha_estimada_final}\n")
        if proy.finalizado:
            f.write(f"   Fecha real de finalizacion     : {proy.fecha_real_final}\n")
        f.write("\n===========================================\n")
    return ruta


def mover_a_finalizados(proy):
    """
    Mueve el recibo de 'Proyectos/{pid}.txt' a 'ProyectosFinalizados/{pid}.txt'
    """
    origen = os.path.join("Proyectos", f"{proy.pid}.txt")
    destino = os.path.join("ProyectosFinalizados", f"{proy.pid}.txt")
    if os.path.exists(origen):
        os.replace(origen, destino)
        return destino
    return None


# ---------------------------------------------------------
#  FUNCIONES PARA GRAFICAS
# ---------------------------------------------------------
def graficar_crecimiento_precio(proy):
    """
    Grafica la proyeccion de crecimiento del precio de venta por m2
    asumiendo 5% anual usando matplotlib.
    """
    print("Mostrando grafica de crecimiento del precio de venta por m2 (5% anual)...")
    anos = 10
    xs = list(range(anos + 1))
    # Convertir precio_venta_m2 (COP) a moneda_actual
    factor = TASA_DE_CONVERSION.get(moneda_actual, 1.0)
    precio_inicial = proy.precio_venta_m2 * factor
    ys = [precio_inicial * ((1 + 0.05) ** t) for t in xs]

    plt.figure()
    plt.plot(xs, ys, marker="o", label=f"Precio Venta m2 ({moneda_actual})")
    plt.title(f"Crecimiento Precio Venta m2 - Proyecto {proy.pid}")
    plt.xlabel("Anios")
    plt.ylabel(f"Precio Venta m2 ({moneda_actual})")
    plt.grid(True)
    plt.legend()
    plt.show()


def graficar_balance(proy):
    """
    Grafica un bar chart comparando inversion (terreno+construccion)
    vs ganancia (20%) en la moneda actual.
    """
    factor = TASA_DE_CONVERSION.get(moneda_actual, 1.0)
    presupuesto = proy.presupuesto_total * factor
    ganancia = proy.ganancia * factor

    print(f"Inversion (terreno + construccion): {SIMBOLO_MONEDA[moneda_actual]} {presupuesto:,.2f} {moneda_actual}")
    print(f"Ganancia estimada (20%):            {SIMBOLO_MONEDA[moneda_actual]} {ganancia:,.2f} {moneda_actual}")

    plt.figure()
    plt.bar(["Inversion", "Ganancia"], [presupuesto, ganancia])
    plt.title(f"Balance Proyecto {proy.pid} ({moneda_actual})")
    plt.ylabel(moneda_actual)
    plt.show()


# ---------------------------------------------------------
#  FUNCIONES PARA LEER DATOS DESDE CONSOLA
# ---------------------------------------------------------
def leer_fecha(prompt, fecha_inicio=None):
    """
    Lee una fecha con formato YYYY-MM-DD. Si se pasa fecha_inicio,
    valida que la fecha ingresada no sea anterior a fecha_inicio.
    """
    while True:
        s = input(prompt).strip()
        if not s:
            return None
        try:
            fecha = datetime.datetime.strptime(s, "%Y-%m-%d").date()
            if fecha_inicio and fecha < fecha_inicio:
                print("  La fecha de finalizacion no puede ser anterior a la fecha de inicio.")
                r = input("  Reintentar? (s/n): ").strip().lower()
                if r != "s":
                    return None
                continue
            return fecha
        except:
            print("  Fecha invalida. Use formato YYYY-MM-DD.")
            r = input("  Reintentar? (s/n): ").strip().lower()
            if r != "s":
                return None


def leer_float(prompt):
    """
    Lee un numero float (permite coma decimal).
    Retorna None si se deja vacio.
    """
    while True:
        s = input(prompt).strip().replace(",", ".")
        if not s:
            return None
        try:
            return float(s)
        except:
            print("  Entrada invalida.")
            r = input("  Reintentar? (s/n): ").strip().lower()
            if r != "s":
                return None


def leer_int(prompt, minimo=None, maximo=None):
    """
    Lee un numero entero y valida rango si se dan minimo y maximo.
    Retorna None si se deja vacio.
    """
    while True:
        s = input(prompt).strip()
        if not s:
            return None
        try:
            v = int(s)
            if minimo is not None and v < minimo:
                print(f"  Debe ser >= {minimo}.")
                continue
            if maximo is not None and v > maximo:
                print(f"  Debe ser <= {maximo}.")
                continue
            return v
        except:
            print("  Entrada invalida.")
            r = input("  Reintentar? (s/n): ").strip().lower()
            if r != "s":
                return None


# ---------------------------------------------------------
#  MENUS Y FLUJO PRINCIPAL
# ---------------------------------------------------------
def menu_opciones(bd):
    """
    Menu para modificar o borrar proyectos, o cambiar moneda.
    """
    global moneda_actual
    while True:
        print("\n=== OPCIONES ===")
        print("1. Modificar datos de un proyecto")
        print("2. Borrar proyecto")
        print("3. Cambiar moneda (COP, USD, EUR)")
        print("4. Volver al menu principal")
        op = input("Opcion: ").strip()

        if op == "1":
            pid = input("ID del proyecto a modificar: ").strip()
            p = bd.obtener(pid)
            if not p:
                print("  Proyecto no encontrado.")
                continue

            print("  Para modificar, ingrese nuevos valores o deje vacio para mantener.")
            nuev_precio = leer_float("  Nuevo precio terreno por m2 (COP): ")
            if nuev_precio is not None:
                p.precio_terreno_m2 = nuev_precio

            nueva_tamano = input("  Nuevo tamano (grande/mediana/chica): ").strip().lower()
            if nueva_tamano in ["grande", "mediana", "chica"]:
                p.tamano = nueva_tamano
                if nueva_tamano == "grande":
                    p.porc_construccion = 80.0
                elif nueva_tamano == "mediana":
                    p.porc_construccion = 60.0
                else:
                    p.porc_construccion = 45.0

            nueva_habit = leer_int("  Nueva cantidad de habitaciones: ", 1)
            if nueva_habit is not None:
                p.habitaciones = nueva_habit

            nuevo_estrato = leer_int("  Nuevo estrato (1-6): ", 1, 6)
            if nuevo_estrato is not None:
                p.estrato = nuevo_estrato
                # Actualizar zonas sociales si cambia estrato
                if p.estrato >= 5:
                    p.zonas_sociales = ["Piscina", "Sauna", "Gimnasio"]
                elif p.estrato == 4:
                    p.zonas_sociales = ["Piscina", "Salon comun"]
                elif p.estrato == 3:
                    p.zonas_sociales = ["Parque infantil", "Salon comun"]
                else:
                    p.zonas_sociales = ["Zonas verdes", "Parque infantil"]

            # Recalcular todo despues de cambios
            p._recalcular()

            ruta = generar_recibo(p)
            bd.agregar(p)
            print(f"  Proyecto modificado y recibo regenerado en: {ruta}")

        elif op == "2":
            pid = input("ID del proyecto a borrar: ").strip()
            p = bd.obtener(pid)
            if not p:
                print("  Proyecto no encontrado.")
                continue
            r = input("  Desea borrar este proyecto? (s/n): ").strip().lower()
            if r == "s":
                bd.eliminar(pid)
                txt = os.path.join("Proyectos", f"{pid}.txt")
                if os.path.exists(txt):
                    os.remove(txt)
                print("  Proyecto borrado.")
            else:
                print("  Operacion cancelada.")

        elif op == "3":
            print(f"  Moneda actual: {moneda_actual}")
            nueva = input("  Ingrese nueva moneda (COP, USD, EUR): ").strip().upper()
            if nueva in ["COP", "USD", "EUR"]:
                moneda_actual = nueva
                print(f"  Moneda cambiada a {moneda_actual}.")
            else:
                print("  Moneda invalida.")

        elif op == "4":
            break

        else:
            print("  Opcion no valida.")


def menu_principal():
    crear_carpetas()
    bd = BaseDeDatos()

    while True:
        print("\n=== MENU PRINCIPAL ===")
        print("1. Registrar Proyecto")
        print("2. Consultar Proyecto")
        print("3. Crecimiento Precio")
        print("4. Balance Proyecto")
        print("5. Finalizar Proyecto")
        print("6. Opciones")
        print("7. Salir")
        op = input("Opcion: ").strip()

        if op == "1":
            # Registrar proyecto nuevo
            pid = input("ID unico del proyecto (sin espacios): ").strip()
            if not pid:
                print("  El ID no puede estar vacio.")
                continue
            if bd.obtener(pid):
                print("  Ya existe un proyecto con ese ID.")
                continue

            tipo = ""
            while tipo not in ["casas", "edificio"]:
                tipo = input("Tipo de proyecto (casas/edificio): ").strip().lower()
                if tipo not in ["casas", "edificio"]:
                    print("  Opcion invalida.")

            fecha_inicio = leer_fecha("Fecha de inicio (YYYY-MM-DD): ")
            if fecha_inicio is None:
                print("  Fecha de inicio requerida.")
                continue

            direccion = input("Direccion del proyecto: ").strip()
            if not direccion:
                print("  La direccion no puede estar vacia.")
                continue

            area_lote = leer_float("Area total del lote (m2): ")
            if area_lote is None:
                continue

            precio_terreno_m2 = leer_float("Precio terreno por m2 (COP): ")
            if precio_terreno_m2 is None:
                continue

            # Tamano de construccion
            tamano = ""
            while tamano not in ["grande", "mediana", "chica"]:
                tamano = input("Tamano de construccion (grande/mediana/chica): ").strip().lower()
                if tamano not in ["grande", "mediana", "chica"]:
                    print("  Opcion invalida.")

            estrato = leer_int("Estrato (1-6): ", 1, 6)
            if estrato is None:
                continue

            # Para casas y edificio pido habitaciones
            habitaciones = None
            if tipo in ["casas", "edificio"]:
                habitaciones = leer_int("Cantidad de habitaciones por unidad (1-5 recomendado): ", 1, 5)
                if habitaciones is None:
                    continue

            fecha_estimada = leer_fecha("Fecha estimada de finalizacion (YYYY-MM-DD): ", fecha_inicio)
            if fecha_estimada is None:
                continue

            # Crear el proyecto y calcular todo internamente
            p = Proyecto(
                pid=pid,
                tipo=tipo,
                fecha_inicio=fecha_inicio,
                direccion=direccion,
                area_lote=area_lote,
                precio_terreno_m2=precio_terreno_m2,
                tamano=tamano,
                estrato=estrato,
                habitaciones=habitaciones,
                fecha_estimada_final=fecha_estimada
            )

            # Mostrar resumen del proyecto ingresado
            print("\n--- Resumen del proyecto ingresado ---")
            print(f"ID                               : {p.pid}")
            print(f"Tipo de proyecto                 : {p.tipo.capitalize()}")
            print(f"Fecha de inicio                  : {p.fecha_inicio}")
            print(f"Direccion                        : {p.direccion}\n")

            print("2. AREAS Y TERRENO")
            print(f"   Area total del lote           : {p.area_lote:,.2f} m2")
            print(f"   Precio terreno por m2         : {formatear_valor(p.precio_terreno_m2)} /m2")
            print(f"   Costo terreno total           : {formatear_valor(p.costo_terreno_total)}")
            print(f"   % Area construida             : {p.porc_construccion:.0f} %")
            print(f"   Area construida               : {p.area_construida:,.2f} m2")
            print(f"   Area no construida            : {p.area_no_construida:,.2f} m2\n")

            print("3. RESTRICCIONES Y VIVIENDAS")
            if p.tipo == "edificio":
                print(f"   Numero de torres              : {p.num_torres}")
                print(f"   Aptos por torre               : {p.aptos_por_torre}")
            print(f"   Habitaciones por unidad       : {p.habitaciones}")
            print(f"   Area minima por unidad        : {p.area_min_vivienda:,.2f} m2")
            print(f"   Numero de unidades estimado   : {p.num_viviendas:,d}")
            print(f"   Valor por unidad              : {formatear_valor(p.valor_casa)}\n")

            print("4. COSTOS Y GANANCIAS")
            print(f"   Costo construccion por m2          : {formatear_valor(p.costo_construccion_m2)} /m2")
            print(f"   Costo construccion total           : {formatear_valor(p.costo_construccion_total)}")
            print(f"   Presupuesto (terreno+construccion) : {formatear_valor(p.presupuesto_total)}")
            print(f"   Ganancia (20%)                     : {formatear_valor(p.ganancia)}")
            print(f"   Precio venta por m2 (derivado)     : {formatear_valor(p.precio_venta_m2)} /m2")
            print(f"   Precio venta total                 : {formatear_valor(p.precio_venta_total)}\n")

            if p.tipo in ["casas", "edificio"]:
                derivada = p.calcular_derivada_valor_por_vivienda()
                if derivada is not None:
                    print(f"   Derivada valor por unidad respecto num unidades: {derivada:,.2f}\n")

            print("5. ZONAS SOCIALES")
            print(f"   {', '.join(p.zonas_sociales)}\n")

            print("6. FECHAS DE FINALIZACION")
            print(f"   Fecha estimada de finalizacion    : {p.fecha_estimada_final}")
            print("   (La fecha real se asigna al finalizar)\n")

            guardar = input("¿Guardar este proyecto? (s/n): ").strip().lower()
            if guardar == "s":
                bd.agregar(p)
                ruta_recibo = generar_recibo(p)
                print(f"  Proyecto guardado. Recibo en: {ruta_recibo}")
            else:
                print("  Proyecto descartado.")

        elif op == "2":
            # Consultar proyecto existente
            proyectos = bd.listar()
            if not proyectos:
                print("  No hay proyectos registrados.")
                continue

            pid = input("ID del proyecto a consultar: ").strip()
            p = bd.obtener(pid)
            if not p:
                print("  Proyecto no encontrado.")
                continue

            # Mostrar datos del proyecto
            print("\n--- Datos del Proyecto ---")
            print(f"ID                               : {p.pid}")
            print(f"Tipo de proyecto                 : {p.tipo.capitalize()}")
            print(f"Fecha de inicio                  : {p.fecha_inicio}")
            print(f"Direccion                        : {p.direccion}\n")

            print("2. AREAS Y TERRENO")
            print(f"   Area total del lote           : {p.area_lote:,.2f} m2")
            print(f"   Precio terreno por m2         : {formatear_valor(p.precio_terreno_m2)} /m2")
            print(f"   Costo terreno total           : {formatear_valor(p.costo_terreno_total)}")
            print(f"   % Area construida             : {p.porc_construccion:.0f} %")
            print(f"   Area construida               : {p.area_construida:,.2f} m2")
            print(f"   Area no construida            : {p.area_no_construida:,.2f} m2\n")

            print("3. RESTRICCIONES Y VIVIENDAS")
            if p.tipo == "edificio":
                print(f"   Numero de torres              : {p.num_torres}")
                print(f"   Aptos por torre               : {p.aptos_por_torre}")
            print(f"   Habitaciones por unidad       : {p.habitaciones}")
            print(f"   Area minima por unidad        : {p.area_min_vivienda:,.2f} m2")
            print(f"   Numero de unidades estimado   : {p.num_viviendas:,d}")
            print(f"   Valor por unidad              : {formatear_valor(p.valor_casa)}\n")

            print("4. COSTOS Y GANANCIAS")
            print(f"   Costo construccion por m2          : {formatear_valor(p.costo_construccion_m2)} /m2")
            print(f"   Costo construccion total           : {formatear_valor(p.costo_construccion_total)}")
            print(f"   Presupuesto total                  : {formatear_valor(p.presupuesto_total)}")
            print(f"   Ganancia (20%)                     : {formatear_valor(p.ganancia)}")
            print(f"   Precio venta por m2 (derivado)     : {formatear_valor(p.precio_venta_m2)} /m2")
            print(f"   Precio venta total                 : {formatear_valor(p.precio_venta_total)}\n")

            if p.tipo in ["casas", "edificio"]:
                derivada = p.calcular_derivada_valor_por_vivienda()
                if derivada is not None:
                    print(f"   Derivada valor por unidad respecto num unidades: {derivada:,.2f}\n")

            print("5. ZONAS SOCIALES")
            print(f"   {', '.join(p.zonas_sociales)}\n")

            print("6. FECHAS DE FINALIZACION")
            print(f"   Fecha estimada de finalizacion    : {p.fecha_estimada_final}")
            if p.finalizado:
                print(f"   Fecha real de finalizacion         : {p.fecha_real_final}")

        elif op == "3":
            # Grafica crecimiento precio
            proyectos = bd.listar()
            if not proyectos:
                print("  No hay proyectos registrados.")
                continue

            pid = input("ID del proyecto para graficar crecimiento precio: ").strip()
            p = bd.obtener(pid)
            if not p:
                print("  Proyecto no encontrado.")
                continue
            graficar_crecimiento_precio(p)

        elif op == "4":
            # Grafica balance proyecto
            proyectos = bd.listar()
            if not proyectos:
                print("  No hay proyectos registrados.")
                continue

            pid = input("ID del proyecto para graficar balance: ").strip()
            p = bd.obtener(pid)
            if not p:
                print("  Proyecto no encontrado.")
                continue
            graficar_balance(p)

        elif op == "5":
            # Finalizar proyecto
            proyectos = bd.listar()
            if not proyectos:
                print("  No hay proyectos registrados.")
                continue

            pid = input("ID del proyecto a finalizar: ").strip()
            p = bd.obtener(pid)
            if not p:
                print("  Proyecto no encontrado.")
                continue

            fecha_real = leer_fecha("Fecha real de finalizacion (YYYY-MM-DD): ", p.fecha_inicio)
            if fecha_real is None:
                continue

            p.finalizado = True
            p.fecha_real_final = fecha_real
            mover_a_finalizados(p)
            bd.eliminar(pid)
            print(f"  Proyecto {pid} finalizado.")

        elif op == "6":
            menu_opciones(bd)

        elif op == "7":
            print("Saliendo...")
            break

        else:
            print("  Opcion no valida.")

if __name__ == "__main__":
    menu_principal()
