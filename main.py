import sys
import math
import numpy as np
import csv
from math import log
from PyQt5 import QtWidgets
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QMainWindow, QApplication, QTableWidget  # , QMessageBox
from astroquery.gaia import Gaia
from astroquery.vizier import Vizier
from astropy.coordinates import Angle
from matplotlib import pyplot
from scipy.stats import linregress as linreg

from LC import LightCurve  # from lightcurves.LC import LightCurve

# Factors:
Ra = -0.02275; Rb = 0.3961; Rc = -0.1243; Rd = -0.01396; Re = 0.003775
Va = -0.02704; Vb = 0.01424; Vc = -0.2156; Vd = 0.01426
Ba = 0.1231; Bb = -2.6513; Bc = 0.0248; Bd = 0.0262

date = []
mag = []
mag_error = []
mag2 = []
mag_error2 = []

with open('PSD data/BL Lac R.CSV', 'r') as file:
    csv_reader = csv.reader(file, delimiter=';')
    next(csv_reader)
    for row in csv_reader:
        date.append(float(row[0]))
        mag.append(float(row[1]))
        mag_error.append(float(row[2]))

time = np.array(date)
flux = 10 ** (-np.array(mag)/2.5)
flux_error = log(10) * flux * np.array(mag_error) / 2.5

lc = LightCurve(time, flux, flux_error)

psd = lc.get_lsp()
slope, inter, rval, pval, stder = linreg(np.log10(psd[0][:int(len(psd[0]/2))]), np.log10(psd[1][:int(len(psd[1]/2))]))

ax = pyplot.axes()
ax.tick_params(axis="both", which="both", direction='in')
x = np.linspace(np.log10(min(psd[0][:int(len(psd[0]/2))])), np.log10(max(psd[0][:int(len(psd[0]/2))])), 10**4)
pyplot.plot(psd[0][:int(len(psd[0]/2))], psd[1][:int(len(psd[1]/2))], color='black', label='BL Lac R', linewidth=1)
pyplot.plot(10 ** x, 10 ** (x * slope + inter), color='crimson', label=f'linear fit, slope {slope:.6f}', linewidth=2.5)

pyplot.grid(color='grey', linestyle='solid')
pyplot.title('Lomb-Scargle periodogram')
pyplot.xlabel('frequency [1/d]')
pyplot.ylabel('power')
pyplot.xscale('log')
pyplot.yscale('log')
pyplot.legend()
print(slope, inter)
#lc.plot_nice()
pyplot.show()


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi("TestUI.ui", self)

        self.lineEdit.setText('BL Lac')

        for i in range(9):
            self.t1.hideColumn(i)

        self.doubleSpinBoxRadius.setValue(0.08)
        self.doubleSpinBoxRadius.setSingleStep(.01)

        self.MagBereich.setMinimum(.5)
        self.MagBereich.setMaximum(5)
        self.MagBereich.setSingleStep(.5)
        self.MagBereich.setValue(1)

        self.Nachkomma.setMinimum(0)
        self.Nachkomma.setMaximum(10)
        self.Nachkomma.setValue(6)

        self.Ergebnisse.setValue(20)

        self.b1.clicked.connect(self.search)
        self.b1.setShortcut("Shift+Return")
        self.actionClose.triggered.connect(lambda: self.closeIt())

    def search(self):
        objectname: str = self.lineEdit.text()
        try:
            result = Vizier.query_region(f"{objectname}", radius=Angle(2.0 / 3600, "deg"), catalog=["I/355/gaiadr3"])
        except:
            self.Object.setText("Couldn't resolve!")
            return
        else:
            pass
        if len(result) == 0:
            return
        else:
            star_id = result[0]['Source'][0]  # BL Lac: "1960066225988786048"; B2 1811: '4591124261934686848'
            self.Object.setText(f'{star_id}')
        radius1: int = self.doubleSpinBoxRadius.value()  # 5 min ~ 0.0833 deg ; whole frame ~ 0.6 deg
        radius = 0
        region: int = self.MagBereich.value()
        digits: int = self.Nachkomma.value()
        ygaia: bool = self.Gaia.isChecked()
        yadistance: bool = self.aDistance.isChecked()
        ergebnisse = self.Ergebnisse.value()
        radeinheit: str = self.comboBoxRadius.currentText()
        if radeinheit == 'deg':
            radius = radius1
        else:
            if radeinheit == 'min':
                radius = radius1 / 60
            if radeinheit == 'sec':
                radius = radius1 / 3600
        query1 = f"SELECT source_id,ra, dec, phot_g_mean_mag, phot_bp_mean_mag, phot_rp_mean_mag, parallax, \
                                pmra, pmdec, phot_variable_flag\
                                FROM gaiadr3.gaia_source \
                                WHERE source_id = {star_id}"
        job1 = Gaia.launch_job(query1)
        results1 = job1.get_results()
        var_obj = results1['phot_variable_flag'][0]
        ra_obj: int = results1['ra'][0]
        dec_obj: int = results1['dec'][0]
        G_obj = results1['phot_g_mean_mag'][0]
        BP_obj = results1['phot_bp_mean_mag'][0]
        RP_obj = results1['phot_rp_mean_mag'][0]
        parallax_obj = results1['parallax'][0]
        pmra_obj = results1['pmra'][0]
        pmdec_obj = results1['pmdec'][0]
        R_obj = G_obj - Ra - (BP_obj - RP_obj) * Rb - (BP_obj - RP_obj) ** 2 * Rc - (BP_obj - RP_obj) ** 3 * Rd - (BP_obj - RP_obj) ** 4 * Re
        V_obj = G_obj - Va - (BP_obj - RP_obj) * Vb - (BP_obj - RP_obj) ** 2 * Vc - (BP_obj - RP_obj) ** 3 * Vd
        B_obj = G_obj - Ba - (V_obj - R_obj) * Bb - (V_obj - R_obj) ** 2 * Bc - (V_obj - R_obj) ** 3 * Bd

        query2 = f"SELECT TOP 2000 \
                                    phot_g_mean_mag, phot_bp_mean_mag, phot_rp_mean_mag, \
                                    phot_g_mean_flux_error, phot_bp_mean_flux_error, phot_rp_mean_flux_error, \
                                    phot_g_mean_flux, phot_bp_mean_flux, phot_rp_mean_flux, \
                                    2.5/log(10) * phot_g_mean_flux_error / phot_g_mean_flux AS phot_g_mean_mag_error,\
                                    2.5/log(10) * phot_bp_mean_flux_error/ phot_bp_mean_flux AS phot_bp_mean_mag_error,\
                                    2.5/log(10) * phot_rp_mean_flux_error/ phot_rp_mean_flux AS phot_rp_mean_mag_error,\
                                    phot_variable_flag, ra, dec, teff_gspphot \
                                 FROM gaiadr3.gaia_source \
                                WHERE \
                                CONTAINS( \
                                        POINT('ICRS',gaiadr3.gaia_source.ra,gaiadr3.gaia_source.dec), \
                                        CIRCLE('ICRS',\
                                                COORD1(EPOCH_PROP_POS({ra_obj},{dec_obj},{parallax_obj},{pmra_obj},{pmdec_obj},0,2000,2016.0)),\
                                                COORD2(EPOCH_PROP_POS({ra_obj},{dec_obj},{parallax_obj},{pmra_obj},{pmdec_obj},0,2000,2016.0)),\
                                                {radius}) \
                                )=1 \
                                AND (phot_g_mean_mag >= {G_obj} - {region} ) \
                                AND (phot_g_mean_mag <= {G_obj} + {region} ) \
                                AND (phot_variable_flag != 'VARIABLE') "  # AND (teff_gspphot != 0)"
        job2 = Gaia.launch_job(query2)
        results2 = job2.get_results()
        ra_star = results2['ra']
        dec_star = results2['dec']
        G_star = results2['phot_g_mean_mag']
        BP_star = results2['phot_bp_mean_mag']
        RP_star = results2['phot_rp_mean_mag']
        eG_star = results2['phot_g_mean_mag_error']
        eBP_star = results2['phot_bp_mean_mag_error']
        eRP_star = results2['phot_rp_mean_mag_error']

        def angular_separation(ra1, dec1, ra2, dec2):
            ra1_rad = math.radians(ra1)
            dec1_rad = math.radians(dec1)
            ra2_rad = math.radians(ra2)
            dec2_rad = math.radians(dec2)
            delta_dec = dec2_rad - dec1_rad
            delta_ra = ra2_rad - ra1_rad
            a = math.sin(delta_dec / 2) ** 2 + math.cos(dec1_rad) * math.cos(dec2_rad) * math.sin(delta_ra / 2) ** 2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            separation = math.degrees(c)
            return separation

        R_star = []; V_star = []; B_star = []
        eR_star = []; eV_star = []; eB_star = []
        angular_distance = []
        row = 0
        sterne = []
        for i in range(len(results2)):
            R_star.append(i)
            V_star.append(i)
            B_star.append(i)
            eR_star.append(i)
            eV_star.append(i)
            eB_star.append(i)
            angular_distance.append(i)
            R_star[i] = G_star[i] - Ra - (BP_star[i] - RP_star[i]) * Rb - (BP_star[i] - RP_star[i]) ** 2 * Rc - (
                    BP_star[i] - RP_star[i]) ** 3 * Rd - (BP_star[i] - RP_star[i]) ** 4 * Re
            V_star[i] = G_star[i] - Va - (BP_star[i] - RP_star[i]) * Vb - (BP_star[i] - RP_star[i]) ** 2 * Vc - (
                    BP_star[i] - RP_star[i]) ** 3 * Vd
            B_star[i] = G_star[i] - Ba - (V_star[i] - R_star[i]) * Bb - (V_star[i] - R_star[i]) ** 2 * Bc - (
                        V_star[i] - R_star[i]) ** 3 * Bd
            angular_distance[i] = angular_separation(ra_star[i], dec_star[i], ra_obj, dec_obj)
            eR_star[i] = ((eG_star[i]) ** 2 + ((-Rb - 2 * Rc * (BP_star[i] - RP_star[i]) - 3 * Rd * (
                        BP_star[i] - RP_star[i]) ** 2 - 4 * Re * (BP_star[i] - RP_star[i]) ** 3) ** 2) * (
                                      (eBP_star[i]) ** 2 + (eRP_star[i]) ** 2)) ** 0.5
            eV_star[i] = ((eG_star[i]) ** 2 + (
                        (-Vb - 2 * Vc * (BP_star[i] - RP_star[i]) - 3 * Vd * (BP_star[i] - RP_star[i]) ** 2) ** 2) * (
                                      (eBP_star[i]) ** 2 + (eRP_star[i]) ** 2)) ** 0.5
            eB_star[i] = ((eG_star[i]) ** 2 + (
                        (-Bb - 2 * Bc * (V_star[i] - R_star[i]) - 3 * Bd * (V_star[i] - R_star[i]) ** 2) ** 2) * (
                                      (eV_star[i]) ** 2 + (eR_star[i]) ** 2)) ** 0.5

        if len(results2) == 0:
            self.l6.setText(f"No Non-Variable stars found around {objectname} within a radius of: {radius:.2f} deg.")
            self.l6.adjustSize()
            for i in range(8):
                self.t1.hideColumn(i)
        else:
            if len(results2) < ergebnisse:
                stuff = len(results2)
            else:
                stuff = ergebnisse
            for i in range(stuff):
                sterne.append(i)
                sterne[i] = {"Ra": f"{ra_star[i]:.5f}", "Dec": f"{dec_star[i]:.5f}",
                             "G": f"{G_star[i]:.{digits}f}",
                             "BP": f"{BP_star[i]:.{digits}f}",
                             "RP": f"{RP_star[i]:.{digits}f}",
                             "R": f"{R_star[i]:.{digits}f} ({eR_star[i]:.{digits}f})",
                             "V": f"{V_star[i]:.{digits}f} ({eV_star[i]:.{digits}f})",
                             "B": f"{B_star[i]:.{digits}f} ({eB_star[i]:.{digits}f})",
                             "Dist": f"{angular_distance[i]:.{digits}f}"}
            self.l6.setText(f'A total of {len(results2)} stars were found. \n'
                            f'Their magnitudes are in the range of G: {G_obj:.2f} +/- {region:.2f} mag. \n'
                            f'Non-Variable stars around {objectname} within a radius of: {radius:.2f} deg.')
            self.l6.adjustSize()
            sorted_stars = sorted(sterne, key=lambda x: x["Dist"])
            self.t1.setRowCount(len(sterne))
            for stern in sorted_stars:
                for i in range(5):
                    self.t1.showColumn(i)
                self.t1.setItem(row, 0, QtWidgets.QTableWidgetItem(stern["Ra"]))
                self.t1.setItem(row, 1, QtWidgets.QTableWidgetItem(stern["Dec"]))
                self.t1.setItem(row, 2, QtWidgets.QTableWidgetItem(stern["R"]))
                self.t1.setItem(row, 3, QtWidgets.QTableWidgetItem(stern["V"]))
                self.t1.setItem(row, 4, QtWidgets.QTableWidgetItem(stern["B"]))
                if ygaia:
                    self.t1.showColumn(5)
                    self.t1.showColumn(6)
                    self.t1.showColumn(7)
                else:
                    self.t1.hideColumn(5)
                    self.t1.hideColumn(6)
                    self.t1.hideColumn(7)
                if yadistance:
                    self.t1.showColumn(8)
                else:
                    self.t1.hideColumn(8)
                self.t1.setItem(row, 5, QtWidgets.QTableWidgetItem(stern["G"]))
                self.t1.setItem(row, 6, QtWidgets.QTableWidgetItem(stern["BP"]))
                self.t1.setItem(row, 7, QtWidgets.QTableWidgetItem(stern["RP"]))
                self.t1.setItem(row, 8, QtWidgets.QTableWidgetItem(stern["Dist"]))
                row += 1
        self.t1.resizeRowsToContents()
        self.t1.resizeColumnsToContents()
        self.t1.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        self.textEdit.setText(f'ra: {ra_obj:.6f} ; dec: {dec_obj:.6f} \n'
                              f'G: {G_obj:.6f}; BP: {BP_obj:.6f}; RP: {RP_obj:.6f} \n'
                              f'R: {R_obj:.6f};  V: {V_obj:.6f};   B: {B_obj:.6f} \n'
                              f'Variable: {var_obj}')

    def closeIt(self):
        self.l1.setText('text')
        sys.exit(0)


#  main
app = QApplication(sys.argv)
mainwindow = MainWindow()
widget = QtWidgets.QStackedWidget()
widget.addWidget(mainwindow)
widget.setGeometry(100, 100, 750, 700)
widget.setWindowTitle("NV-StarFinder")
widget.show()
try:
    pass #sys.exit(app.exec_())
finally:
    pass
