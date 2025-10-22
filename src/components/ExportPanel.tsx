import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Download, FileJson, FileText, FileCode } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { exportAsSVG, exportAsDXF, exportAsJSON, downloadFile, FloorPlanData } from '@/utils/exportUtils';

interface ExportPanelProps {
  hasFloorPlan: boolean;
  floorPlanData?: FloorPlanData;
}

export function ExportPanel({ hasFloorPlan, floorPlanData }: ExportPanelProps) {
  const { toast } = useToast();

  const handleExport = (format: string) => {
    if (!hasFloorPlan || !floorPlanData) {
      toast({
        title: 'No floor plan',
        description: 'Generate a floor plan first to export',
        variant: 'destructive',
      });
      return;
    }

    try {
      let content: string;
      let filename: string;
      let mimeType: string;

      switch (format) {
        case 'svg':
          content = exportAsSVG(floorPlanData);
          filename = 'floor-plan.svg';
          mimeType = 'image/svg+xml';
          break;
        case 'dxf':
          content = exportAsDXF(floorPlanData);
          filename = 'floor-plan.dxf';
          mimeType = 'application/dxf';
          break;
        case 'json':
          content = exportAsJSON(floorPlanData);
          filename = 'floor-plan.json';
          mimeType = 'application/json';
          break;
        default:
          throw new Error('Unsupported format');
      }

      downloadFile(content, filename, mimeType);

      toast({
        title: 'Export successful',
        description: `Floor plan exported as ${format.toUpperCase()}`,
      });
    } catch (error) {
      toast({
        title: 'Export failed',
        description: 'Could not export floor plan',
        variant: 'destructive',
      });
    }
  };

  return (
    <Card className="p-6">
      <h3 className="mb-4 text-lg font-semibold">Export Options</h3>
      <div className="space-y-3">
        <Button
          variant="outline"
          className="w-full justify-start"
          onClick={() => handleExport('svg')}
          disabled={!hasFloorPlan}
        >
          <Download className="mr-2 h-4 w-4" />
          Export as SVG
        </Button>
        <Button
          variant="outline"
          className="w-full justify-start"
          onClick={() => handleExport('dxf')}
          disabled={!hasFloorPlan}
        >
          <FileCode className="mr-2 h-4 w-4" />
          Export as DXF (CAD)
        </Button>
        <Button
          variant="outline"
          className="w-full justify-start"
          onClick={() => handleExport('json')}
          disabled={!hasFloorPlan}
        >
          <FileJson className="mr-2 h-4 w-4" />
          Export as JSON
        </Button>
      </div>
    </Card>
  );
}
