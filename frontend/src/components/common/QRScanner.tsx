import { useEffect, useRef, useState } from 'react';
import { Html5Qrcode } from 'html5-qrcode';
import { Paper, Stack, Text, Button, Alert, Group } from '@mantine/core';
import { IconCamera, IconX, IconAlertCircle } from '@tabler/icons-react';

interface QRScannerProps {
  onScan: (code: string) => void;
  onClose?: () => void;
}

export default function QRScanner({ onScan, onClose }: QRScannerProps) {
  const [error, setError] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(true);
  const scannerRef = useRef<Html5Qrcode | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const containerId = 'qr-reader';
    
    // Initialize scanner
    const initScanner = async () => {
      try {
        const scanner = new Html5Qrcode(containerId);
        scannerRef.current = scanner;

        await scanner.start(
          { facingMode: 'environment' },
          {
            fps: 10,
            qrbox: { width: 250, height: 250 },
          },
          (decodedText) => {
            // Success callback
            onScan(decodedText);
            scanner.stop().catch(console.error);
          },
          () => {
            // Error callback (called frequently, ignore)
          }
        );
        
        setIsStarting(false);
      } catch (err) {
        console.error('Scanner error:', err);
        setError(
          err instanceof Error
            ? err.message
            : 'Impossibile accedere alla fotocamera'
        );
        setIsStarting(false);
      }
    };

    initScanner();

    // Cleanup
    return () => {
      if (scannerRef.current) {
        scannerRef.current.stop().catch(console.error);
      }
    };
  }, [onScan]);

  return (
    <Paper withBorder p="md" radius="md" ref={containerRef}>
      <Stack>
        <Group justify="space-between">
          <Group gap="xs">
            <IconCamera size={20} />
            <Text fw={500}>Scanner QR</Text>
          </Group>
          {onClose && (
            <Button
              variant="subtle"
              color="gray"
              size="sm"
              onClick={onClose}
              leftSection={<IconX size={16} />}
            >
              Chiudi
            </Button>
          )}
        </Group>

        {error ? (
          <Alert icon={<IconAlertCircle size={16} />} color="red" variant="light">
            {error}
            <Text size="sm" mt="xs">
              Assicurati di aver concesso i permessi alla fotocamera.
            </Text>
          </Alert>
        ) : (
          <>
            {isStarting && (
              <Text ta="center" c="dimmed">
                Inizializzazione fotocamera...
              </Text>
            )}
            <div
              id="qr-reader"
              style={{
                width: '100%',
                maxWidth: '400px',
                margin: '0 auto',
              }}
            />
            <Text size="xs" c="dimmed" ta="center">
              Inquadra il codice QR
            </Text>
          </>
        )}
      </Stack>
    </Paper>
  );
}

