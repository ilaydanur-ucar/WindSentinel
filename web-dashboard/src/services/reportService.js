import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

/**
 * Generate and download a CSV file.
 * BOM prefix ensures Turkish characters display correctly in Excel.
 */
export function generateCSV(data, columns, filename = 'report.csv') {
  const BOM = '\uFEFF';
  const header = columns.map(c => c.label).join(';');
  const rows = data.map(row =>
    columns.map(c => {
      const val = typeof c.format === 'function' ? c.format(row[c.key], row) : row[c.key];
      return `"${String(val ?? '').replace(/"/g, '""')}"`;
    }).join(';')
  );

  const csv = BOM + header + '\n' + rows.join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  downloadBlob(blob, filename);
}

/**
 * Generate and download a PDF report with table.
 */
export function generatePDF(data, columns, title, filename = 'report.pdf') {
  const doc = new jsPDF();

  // Header
  doc.setFontSize(18);
  doc.setTextColor(45, 74, 111);
  doc.text('WIND Sentinel', 14, 20);

  doc.setFontSize(11);
  doc.setTextColor(100, 116, 139);
  doc.text(title, 14, 28);

  doc.setFontSize(9);
  doc.text(new Date().toLocaleString('tr-TR'), 14, 34);

  // Divider
  doc.setDrawColor(200, 210, 225);
  doc.line(14, 37, 196, 37);

  // Table
  const head = [columns.map(c => c.label)];
  const body = data.map(row =>
    columns.map(c => {
      const val = typeof c.format === 'function' ? c.format(row[c.key], row) : row[c.key];
      return String(val ?? '');
    })
  );

  autoTable(doc, {
    startY: 42,
    head,
    body,
    styles: { fontSize: 9, cellPadding: 3 },
    headStyles: { fillColor: [45, 74, 111], textColor: 255, fontStyle: 'bold' },
    alternateRowStyles: { fillColor: [243, 245, 249] },
    margin: { left: 14, right: 14 },
  });

  // Footer
  const pageCount = doc.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(148, 163, 184);
    doc.text(`WIND Sentinel Report - ${i}/${pageCount}`, 14, 290);
  }

  doc.save(filename);
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
