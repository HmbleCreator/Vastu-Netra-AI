import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { CheckCircle2, AlertCircle } from 'lucide-react';

interface VastuScore {
  overall: number;
  entranceCompliance: number;
  roomPlacement: number;
  directionAlignment: number;
}

interface VastuScoreCardProps {
  score?: VastuScore;
}

export function VastuScoreCard({ score }: VastuScoreCardProps) {
  if (!score) {
    return (
      <Card className="p-6">
        <h3 className="mb-4 text-lg font-semibold">Vastu Compliance</h3>
        <p className="text-sm text-muted-foreground">
          Generate a floor plan to see Vastu compliance score
        </p>
      </Card>
    );
  }

  const getScoreColor = (value: number) => {
    if (value >= 80) return 'text-green-600';
    if (value >= 60) return 'text-amber-600';
    return 'text-red-600';
  };

  const getScoreIcon = (value: number) => {
    if (value >= 80) return <CheckCircle2 className="h-5 w-5 text-green-600" />;
    return <AlertCircle className="h-5 w-5 text-amber-600" />;
  };

  return (
    <Card className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold">Vastu Compliance</h3>
        <div className="flex items-center gap-2">
          {getScoreIcon(score.overall)}
          <span className={`text-2xl font-bold ${getScoreColor(score.overall)}`}>
            {score.overall}%
          </span>
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <div className="mb-1 flex justify-between text-sm">
            <span>Entrance Compliance</span>
            <span className="font-medium">{score.entranceCompliance}%</span>
          </div>
          <Progress value={score.entranceCompliance} />
        </div>

        <div>
          <div className="mb-1 flex justify-between text-sm">
            <span>Room Placement</span>
            <span className="font-medium">{score.roomPlacement}%</span>
          </div>
          <Progress value={score.roomPlacement} />
        </div>

        <div>
          <div className="mb-1 flex justify-between text-sm">
            <span>Direction Alignment</span>
            <span className="font-medium">{score.directionAlignment}%</span>
          </div>
          <Progress value={score.directionAlignment} />
        </div>
      </div>
    </Card>
  );
}
