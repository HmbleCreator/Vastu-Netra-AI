import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Settings } from 'lucide-react';

export type LLMType = 'browser' | 'ollama' | 'llamacpp' | 'lmstudio';

export interface LLMConfig {
  type: LLMType;
  endpoint: string;
  model: string;
}

interface LLMSettingsProps {
  config: LLMConfig;
  onConfigChange: (config: LLMConfig) => void;
}

const DEFAULT_ENDPOINTS: Record<LLMType, string> = {
  browser: '',
  ollama: 'http://localhost:11434',
  llamacpp: 'http://localhost:8080',
  lmstudio: 'http://localhost:1234',
};

export function LLMSettings({ config, onConfigChange }: LLMSettingsProps) {
  const [open, setOpen] = useState(false);
  const [localConfig, setLocalConfig] = useState(config);

  const handleSave = () => {
    onConfigChange(localConfig);
    setOpen(false);
  };

  const handleTypeChange = (type: LLMType) => {
    setLocalConfig({
      ...localConfig,
      type,
      endpoint: DEFAULT_ENDPOINTS[type],
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Settings className="mr-2 h-4 w-4" />
          LLM Settings
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>LLM Configuration</DialogTitle>
        </DialogHeader>
        <div className="space-y-6 py-4">
          <div className="space-y-3">
            <Label>LLM Type</Label>
            <RadioGroup value={localConfig.type} onValueChange={(value) => handleTypeChange(value as LLMType)}>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="browser" id="browser" />
                <Label htmlFor="browser" className="font-normal">Browser (WebGPU)</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="ollama" id="ollama" />
                <Label htmlFor="ollama" className="font-normal">Ollama</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="llamacpp" id="llamacpp" />
                <Label htmlFor="llamacpp" className="font-normal">llama.cpp Server</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="lmstudio" id="lmstudio" />
                <Label htmlFor="lmstudio" className="font-normal">LM Studio</Label>
              </div>
            </RadioGroup>
          </div>

          {localConfig.type !== 'browser' && (
            <>
              <div className="space-y-2">
                <Label htmlFor="endpoint">API Endpoint</Label>
                <Input
                  id="endpoint"
                  value={localConfig.endpoint}
                  onChange={(e) => setLocalConfig({ ...localConfig, endpoint: e.target.value })}
                  placeholder="http://localhost:11434"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="model">Model Name</Label>
                <Input
                  id="model"
                  value={localConfig.model}
                  onChange={(e) => setLocalConfig({ ...localConfig, model: e.target.value })}
                  placeholder="llama3.2, mistral, etc."
                />
              </div>
            </>
          )}
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={handleSave}>Save</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
