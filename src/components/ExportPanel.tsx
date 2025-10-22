import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Download, FileJson, FileText } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface ExportPanelProps {
  hasFloorPlan: boolean;
}

export function ExportPanel({ hasFloorPlan }: ExportPanelProps) {
  const { toast } = useToast();

  const handleExport = (format: string) => {
    if (!hasFloorPlan) {
      toast({
        title: 'No floor plan',
        description: 'Generate a floor plan first to export',
        variant: 'destructive',
      });
      return;
    }

    toast({
      title: 'Export started',
      description: `Exporting floor plan as ${format.toUpperCase()}...`,
    });

    // TODO: Implement actual export logic
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
          onClick={() => handleExport('pdf')}
          disabled={!hasFloorPlan}
        >
          <FileText className="mr-2 h-4 w-4" />
          Export as PDF
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
