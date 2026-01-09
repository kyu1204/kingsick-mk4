'use client';

import { useState, useEffect, useCallback } from 'react';
import { Key, Loader2, AlertCircle, CheckCircle, Trash2, Eye, EyeOff, ShieldCheck } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  ApiKeyInfo,
  SaveApiKeyRequest,
  getApiKeyInfo,
  saveApiKey,
  deleteApiKey,
  verifyApiKey,
} from '@/lib/api/api-keys';

export function ApiKeySettings() {
  const [apiKeyInfo, setApiKeyInfo] = useState<ApiKeyInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [appKey, setAppKey] = useState('');
  const [appSecret, setAppSecret] = useState('');
  const [accountNo, setAccountNo] = useState('');
  const [isPaperTrading, setIsPaperTrading] = useState(true);
  const [showSecret, setShowSecret] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Verify state
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState<{ valid: boolean; message: string } | null>(null);

  // Delete dialog state
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const loadApiKeyInfo = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const info = await getApiKeyInfo();
      setApiKeyInfo(info);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load API key info');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadApiKeyInfo();
  }, [loadApiKeyInfo]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setIsSaving(true);

    try {
      const request: SaveApiKeyRequest = {
        app_key: appKey,
        app_secret: appSecret,
        account_no: accountNo,
        is_paper_trading: isPaperTrading,
      };
      await saveApiKey(request);
      setSuccess('API key saved successfully');
      setShowForm(false);
      setAppKey('');
      setAppSecret('');
      setAccountNo('');
      await loadApiKeyInfo();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save API key');
    } finally {
      setIsSaving(false);
    }
  };

  const handleVerify = async () => {
    setIsVerifying(true);
    setVerifyResult(null);
    try {
      const result = await verifyApiKey();
      setVerifyResult(result);
    } catch (err) {
      setVerifyResult({
        valid: false,
        message: err instanceof Error ? err.message : 'Verification failed',
      });
    } finally {
      setIsVerifying(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    setError(null);
    try {
      await deleteApiKey();
      setSuccess('API key deleted successfully');
      setShowDeleteDialog(false);
      await loadApiKeyInfo();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete API key');
    } finally {
      setIsDeleting(false);
    }
  };

  // Clear messages after 5 seconds
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  useEffect(() => {
    if (verifyResult) {
      const timer = setTimeout(() => setVerifyResult(null), 10000);
      return () => clearTimeout(timer);
    }
  }, [verifyResult]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            Korea Investment API
          </CardTitle>
          <CardDescription>
            Connect your brokerage account for live trading
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Key className="h-5 w-5" />
          Korea Investment API
        </CardTitle>
        <CardDescription>
          Connect your brokerage account for live trading
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Error/Success messages */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {success && (
          <Alert className="border-green-500/50 bg-green-500/10">
            <CheckCircle className="h-4 w-4 text-green-500" />
            <AlertDescription className="text-green-500">{success}</AlertDescription>
          </Alert>
        )}
        {verifyResult && (
          <Alert className={verifyResult.valid ? 'border-green-500/50 bg-green-500/10' : 'border-destructive'}>
            {verifyResult.valid ? (
              <CheckCircle className="h-4 w-4 text-green-500" />
            ) : (
              <AlertCircle className="h-4 w-4" />
            )}
            <AlertDescription className={verifyResult.valid ? 'text-green-500' : ''}>
              {verifyResult.message}
            </AlertDescription>
          </Alert>
        )}

        {/* Current API Key Info or Form */}
        {apiKeyInfo?.has_api_key && !showForm ? (
          <>
            {/* Connected state */}
            <div className="flex items-center justify-between p-4 border rounded-lg bg-green-500/10 border-green-500/20">
              <div>
                <p className="font-medium text-green-500">Connected</p>
                <p className="text-sm text-muted-foreground">
                  App Key: {apiKeyInfo.app_key_masked}
                </p>
                <p className="text-sm text-muted-foreground">
                  Account: {apiKeyInfo.account_no_masked}
                </p>
              </div>
              <div className="flex flex-col items-end gap-1">
                <Badge variant={apiKeyInfo.is_paper_trading ? 'secondary' : 'profit'}>
                  {apiKeyInfo.is_paper_trading ? 'Paper Trading' : 'Live'}
                </Badge>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setShowForm(true)}
              >
                Update API Key
              </Button>
              <Button
                variant="outline"
                onClick={handleVerify}
                disabled={isVerifying}
              >
                {isVerifying ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ShieldCheck className="h-4 w-4" />
                )}
              </Button>
              <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
                <DialogTrigger asChild>
                  <Button variant="outline" className="text-destructive hover:bg-destructive/10">
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Delete API Key</DialogTitle>
                    <DialogDescription>
                      Are you sure you want to delete your API credentials? This action cannot be undone.
                      You will need to re-enter your credentials to continue trading.
                    </DialogDescription>
                  </DialogHeader>
                  <DialogFooter>
                    <Button
                      variant="outline"
                      onClick={() => setShowDeleteDialog(false)}
                      disabled={isDeleting}
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={handleDelete}
                      disabled={isDeleting}
                    >
                      {isDeleting ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Deleting...
                        </>
                      ) : (
                        'Delete'
                      )}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          </>
        ) : (
          <>
            {/* Form */}
            <form onSubmit={handleSave} className="space-y-4">
              {!apiKeyInfo?.has_api_key && (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Connect your Korea Investment API to enable live trading.
                    You can get your API credentials from the KIS developer portal.
                  </AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                <label htmlFor="appKey" className="text-sm font-medium">
                  App Key
                </label>
                <Input
                  id="appKey"
                  type="text"
                  placeholder="Enter your App Key"
                  value={appKey}
                  onChange={(e) => setAppKey(e.target.value)}
                  required
                  disabled={isSaving}
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="appSecret" className="text-sm font-medium">
                  App Secret
                </label>
                <div className="relative">
                  <Input
                    id="appSecret"
                    type={showSecret ? 'text' : 'password'}
                    placeholder="Enter your App Secret"
                    value={appSecret}
                    onChange={(e) => setAppSecret(e.target.value)}
                    required
                    disabled={isSaving}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                    onClick={() => setShowSecret(!showSecret)}
                  >
                    {showSecret ? (
                      <EyeOff className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <Eye className="h-4 w-4 text-muted-foreground" />
                    )}
                  </Button>
                </div>
              </div>

              <div className="space-y-2">
                <label htmlFor="accountNo" className="text-sm font-medium">
                  Account Number
                </label>
                <Input
                  id="accountNo"
                  type="text"
                  placeholder="Enter your account number"
                  value={accountNo}
                  onChange={(e) => setAccountNo(e.target.value)}
                  required
                  disabled={isSaving}
                />
              </div>

              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium">Paper Trading Mode</p>
                  <p className="text-sm text-muted-foreground">
                    Test with virtual trades (recommended for testing)
                  </p>
                </div>
                <Switch
                  checked={isPaperTrading}
                  onCheckedChange={setIsPaperTrading}
                  disabled={isSaving}
                />
              </div>

              {!isPaperTrading && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Live trading mode will execute real trades with real money.
                    Make sure you understand the risks involved.
                  </AlertDescription>
                </Alert>
              )}

              <div className="flex gap-2">
                {showForm && apiKeyInfo?.has_api_key && (
                  <Button
                    type="button"
                    variant="outline"
                    className="flex-1"
                    onClick={() => {
                      setShowForm(false);
                      setAppKey('');
                      setAppSecret('');
                      setAccountNo('');
                    }}
                    disabled={isSaving}
                  >
                    Cancel
                  </Button>
                )}
                <Button type="submit" className="flex-1" disabled={isSaving}>
                  {isSaving ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    'Save API Key'
                  )}
                </Button>
              </div>
            </form>
          </>
        )}
      </CardContent>
    </Card>
  );
}
