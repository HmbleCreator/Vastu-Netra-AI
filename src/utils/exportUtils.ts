import makerjs from 'makerjs';

export interface Room {
  id: string;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  type: string;
}

export interface FloorPlanData {
  rooms: Room[];
  plotWidth: number;
  plotLength: number;
  plotShape?: 'rectangular' | 'L-shaped' | 'T-shaped' | 'irregular';
  landscapeZones?: Array<{
    id: string;
    name: string;
    type: 'garden' | 'lawn' | 'parking' | 'driveway';
    points: Array<{ x: number; y: number }>;
  }>;
}

/**
 * Export floor plan as SVG string
 */
export function exportAsSVG(data: FloorPlanData): string {
  const { rooms, plotWidth, plotLength } = data;
  const scale = 50; // pixels per meter
  const width = plotWidth * scale;
  const height = plotLength * scale;

  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`;
  svg += `<rect width="${width}" height="${height}" fill="#f5f5f5" stroke="#333" stroke-width="2"/>`;

  // Draw rooms
  rooms.forEach((room) => {
    const x = room.x * scale;
    const y = room.y * scale;
    const w = room.width * scale;
    const h = room.height * scale;

    svg += `<g>`;
    svg += `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="#fff" stroke="#333" stroke-width="1.5"/>`;
    svg += `<text x="${x + w / 2}" y="${y + h / 2}" text-anchor="middle" dominant-baseline="middle" font-family="Arial" font-size="12" fill="#333">${room.name}</text>`;
    svg += `<text x="${x + w / 2}" y="${y + h / 2 + 15}" text-anchor="middle" dominant-baseline="middle" font-family="Arial" font-size="10" fill="#666">${room.width}m × ${room.height}m</text>`;
    svg += `</g>`;
  });

  svg += `</svg>`;
  return svg;
}

/**
 * Export floor plan as DXF string (CAD format)
 */
export function exportAsDXF(data: FloorPlanData): string {
  const { rooms, plotWidth, plotLength } = data;
  
  // Create a basic makerjs model using the correct API
  const model: makerjs.IModel = {
    models: {
      plot: new makerjs.models.Rectangle(plotWidth, plotLength)
    }
  };

  // Add rooms as nested models
  rooms.forEach((room, index) => {
    if (!model.models) model.models = {};
    const roomModel = new makerjs.models.Rectangle(room.width, room.height);
    roomModel.origin = [room.x, room.y];
    model.models[`room_${index}`] = roomModel;
  });

  // Convert to DXF using makerjs exporter
  const dxf = makerjs.exporter.toDXF(model);
  return dxf;
}

/**
 * Export floor plan as JSON with complete metadata
 */
export function exportAsJSON(data: FloorPlanData): string {
  const exportData = {
    version: '1.0',
    timestamp: new Date().toISOString(),
    plot: {
      width: data.plotWidth,
      length: data.plotLength,
      shape: data.plotShape || 'rectangular',
      area: data.plotWidth * data.plotLength
    },
    rooms: data.rooms.map(room => ({
      id: room.id,
      name: room.name,
      type: room.type,
      position: { x: room.x, y: room.y },
      dimensions: { width: room.width, height: room.height },
      area: room.width * room.height,
      center: {
        x: room.x + room.width / 2,
        y: room.y + room.height / 2
      }
    })),
    landscapeZones: data.landscapeZones || [],
    statistics: {
      totalRooms: data.rooms.length,
      totalBuiltUpArea: data.rooms.reduce((sum, r) => sum + (r.width * r.height), 0),
      roomTypes: data.rooms.reduce((acc, r) => {
        acc[r.type] = (acc[r.type] || 0) + 1;
        return acc;
      }, {} as Record<string, number>)
    }
  };

  return JSON.stringify(exportData, null, 2);
}

/**
 * Trigger download of exported file
 */
export function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Export as PDF (converts SVG to PDF)
 */
export async function exportAsPDF(data: FloorPlanData): Promise<void> {
  // Import dynamically to avoid SSR issues
  const { jsPDF } = await import('jspdf');
  const svg2pdf = (await import('svg2pdf.js')).default;
  
  // Generate SVG first
  const svg = exportAsSVG(data);
  
  try {
    // Create a new jsPDF instance
    const doc = new jsPDF({
      orientation: 'landscape',
      unit: 'mm',
      format: 'a4'
    });
    
    // Create an SVG element from the string
    const svgElement = document.createElement('div');
    svgElement.innerHTML = svg;
    const svgNode = svgElement.firstChild as SVGElement;
    
    // Convert SVG to PDF
    await svg2pdf(svgNode, doc, {
      xOffset: 10,
      yOffset: 10,
      scale: 0.7
    });
    
    // Save the PDF
    doc.save('floor-plan.pdf');
  } catch (error) {
    console.error('Error generating PDF:', error);
    // Fallback to SVG if PDF generation fails
    downloadFile(svg, 'floor-plan.svg', 'image/svg+xml');
  }
}
