import { Card } from '@/components/ui/card';

interface FloorPlanViewerProps {
  svgData?: string;
}

export function FloorPlanViewer({ svgData }: FloorPlanViewerProps) {
  if (!svgData) {
    return (
      <Card className="flex h-full items-center justify-center border-2 border-dashed border-border blueprint-grid">
        <div className="text-center text-muted-foreground">
          <p className="text-lg font-medium">No floor plan yet</p>
          <p className="text-sm">Start chatting to generate your Vastu-compliant design</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="h-full overflow-hidden border-2 border-border">
      <div className="h-full w-full overflow-auto p-4">
        <div
          className="flex items-center justify-center"
          dangerouslySetInnerHTML={{ __html: svgData }}
        />
      </div>
    </Card>
  );
}
