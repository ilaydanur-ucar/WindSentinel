import { useState, createContext, useContext } from 'react';

const translations = {
  tr: {
    // Nav
    dashboard: 'Kontrol Paneli',
    turbines: 'Türbinler',
    alarms: 'Alarmlar',
    systemStatus: 'Sistem Durumu',
    monitoring: 'İzleme',
    system: 'Sistem',
    logout: 'Çıkış Yap',
    live: 'CANLI',
    searchTurbine: 'Türbin ara...',
    subtitle: 'Erken Arıza Tespit Sistemi',

    // Dashboard
    controlPanel: 'Kontrol Paneli',
    realTimeMonitoring: 'Gerçek zamanlı izleme',
    last24h: 'Son 24 Saat',
    activeTurbine: 'Aktif Türbin',
    allOperational: 'Tümü operasyonel',
    offline: 'devre dışı',
    resolutionRate: 'Çözüm Oranı',
    resolved: 'çözüldü',
    avgRiskScore: 'Ort. Risk Skoru',
    points100: '/100 puan',
    activeAlarm: 'Aktif Alarm',
    turbinesAffected: 'türbin etkilendi',
    turbineRiskStatus: 'Türbin Risk Durumu',
    activeAlarms: 'Aktif Alarmlar',
    all: 'Tümü',
    riskScoreTrend: 'Risk Skoru Trendi',
    manualMeasurement: 'Manuel Ölçüm',
    enterSensorValues: 'Sensör değerlerini girin',
    calculateRisk: 'Risk Hesapla',
    calculating: 'Hesaplanıyor...',
    riskScore: 'Risk Skoru',
    powerDeviation: 'Güç Sapması',
    tempRisk: 'Sıcaklık Riski',
    vibRisk: 'Titreşim Riski',
    noActiveAlarm: 'Aktif alarm yok',
    systemHealthy: 'Sistem sağlıklı çalışıyor',
    farm: 'Çiftlik',
    status: 'Durum',
    alarm: 'Alarm',
    active: 'AKTİF',
    closed: 'KAPALI',
    loading: 'Yükleniyor...',

    // Alarms
    alarmManagement: 'Alarm Yönetimi',
    anomalyResults: 'Anomali tespit sonuçları ve alarm geçmişi',
    allFilter: 'Tümü',
    activeFilter: 'Aktif',
    resolvedFilter: 'İncelendi',
    records: 'kayıt',
    id: 'ID',
    turbine: 'Türbin',
    type: 'Tür',
    score: 'Skor',
    confidence: 'Güven',
    date: 'Tarih',
    action: 'İşlem',
    resolve: 'Çöz',
    resolvedStatus: 'İncelendi',
    activeStatus: 'Aktif',
    notFound: 'Alarm bulunamadı',

    // Turbines
    turbineStatuses: 'Türbin Durumları',
    realTimeData: 'Gerçek zamanlı izleme verileri',
    activeAlarmLabel: 'Aktif Alarm',
    farmLabel: 'Çiftlik',
    back: 'Geri',
    alarmHistory: 'Alarm Geçmişi',
    activeAlarmsLabel: 'Aktif Alarmlar',
    resolvedLabel: 'İncelendi',
    totalEvents: 'Toplam Olay',
    noAlarmRecorded: 'Bu türbin için alarm kaydedilmemiş',
    critical: 'KRİTİK',
    warning: 'UYARI',
    info: 'BİLGİ',
    normal: 'NORMAL',

    // Severity
    severityCritical: 'Kritik',
    severityWarning: 'Uyarı',
    severityActive: 'Aktif',

    // Manual measurement
    windSpeed: 'Rüzgâr Hızı',
    powerOutput: 'Güç Üretimi',
    generatorRpm: 'Jeneratör RPM',
    gearboxTemp: 'Dişli Kutusu Sıcaklığı',
    vibrationLevel: 'Titreşim Seviyesi',

    // Login
    loginTitle: 'Giriş Yap',
    loginSubtitle: 'Türbin izleme paneline erişim için giriş yapın.',
    email: 'E-posta',
    password: 'Şifre',
    loggingIn: 'Giriş yapılıyor...',
    login: 'Giriş Yap',

    // Time
    justNow: 'Az önce',
    minutesAgo: 'dk önce',
    hoursAgo: 'saat önce',
    daysAgo: 'gün önce',
  },
  en: {
    dashboard: 'Dashboard',
    turbines: 'Turbines',
    alarms: 'Alarms',
    systemStatus: 'System Status',
    monitoring: 'Monitoring',
    system: 'System',
    logout: 'Logout',
    live: 'LIVE',
    searchTurbine: 'Search turbine...',
    subtitle: 'Early Fault Detection System',

    controlPanel: 'Dashboard',
    realTimeMonitoring: 'Real-time monitoring',
    last24h: 'Last 24 Hours',
    activeTurbine: 'Active Turbines',
    allOperational: 'All operational',
    offline: 'offline',
    resolutionRate: 'Resolution Rate',
    resolved: 'resolved',
    avgRiskScore: 'Avg. Risk Score',
    points100: '/100 points',
    activeAlarm: 'Active Alarms',
    turbinesAffected: 'turbines affected',
    turbineRiskStatus: 'Turbine Risk Status',
    activeAlarms: 'Active Alarms',
    all: 'All',
    riskScoreTrend: 'Risk Score Trend',
    manualMeasurement: 'Manual Measurement',
    enterSensorValues: 'Enter sensor values',
    calculateRisk: 'Calculate Risk',
    calculating: 'Calculating...',
    riskScore: 'Risk Score',
    powerDeviation: 'Power Deviation',
    tempRisk: 'Temperature Risk',
    vibRisk: 'Vibration Risk',
    noActiveAlarm: 'No active alarms',
    systemHealthy: 'System running healthy',
    farm: 'Farm',
    status: 'Status',
    alarm: 'Alarm',
    active: 'ACTIVE',
    closed: 'OFFLINE',
    loading: 'Loading...',

    alarmManagement: 'Alarm Management',
    anomalyResults: 'Anomaly detection results and alarm history',
    allFilter: 'All',
    activeFilter: 'Active',
    resolvedFilter: 'Resolved',
    records: 'records',
    id: 'ID',
    turbine: 'Turbine',
    type: 'Type',
    score: 'Score',
    confidence: 'Confidence',
    date: 'Date',
    action: 'Action',
    resolve: 'Resolve',
    resolvedStatus: 'Resolved',
    activeStatus: 'Active',
    notFound: 'No alarms found',

    turbineStatuses: 'Turbine Status',
    realTimeData: 'Real-time monitoring data',
    activeAlarmLabel: 'Active Alarms',
    farmLabel: 'Farm',
    back: 'Back',
    alarmHistory: 'Alarm History',
    activeAlarmsLabel: 'Active Alarms',
    resolvedLabel: 'Resolved',
    totalEvents: 'Total Events',
    noAlarmRecorded: 'No alarms recorded for this turbine',
    critical: 'CRITICAL',
    warning: 'WARNING',
    info: 'INFO',
    normal: 'NORMAL',

    severityCritical: 'Critical',
    severityWarning: 'Warning',
    severityActive: 'Active',

    windSpeed: 'Wind Speed',
    powerOutput: 'Power Output',
    generatorRpm: 'Generator RPM',
    gearboxTemp: 'Gearbox Temperature',
    vibrationLevel: 'Vibration Level',

    loginTitle: 'Sign In',
    loginSubtitle: 'Sign in to access the turbine monitoring panel.',
    email: 'Email',
    password: 'Password',
    loggingIn: 'Signing in...',
    login: 'Sign In',

    justNow: 'Just now',
    minutesAgo: 'min ago',
    hoursAgo: 'hours ago',
    daysAgo: 'days ago',
  },
};

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem('windsentinel_lang') || 'tr');

  const changeLang = (newLang) => {
    setLang(newLang);
    localStorage.setItem('windsentinel_lang', newLang);
  };

  const t = (key) => translations[lang]?.[key] || translations.tr[key] || key;

  return (
    <LanguageContext.Provider value={{ lang, setLang: changeLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
