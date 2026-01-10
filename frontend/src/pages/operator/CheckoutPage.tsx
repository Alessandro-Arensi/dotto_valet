import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Title,
  Text,
  Paper,
  Group,
  Stack,
  Button,
  Alert,
  Image,
  Badge,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconQrcode, IconCheck, IconMapPin, IconClock } from '@tabler/icons-react';

import { checkinApi, CheckoutResponse } from '../../api/client';
import QRScanner from '../../components/common/QRScanner';

export default function CheckoutPage() {
  const queryClient = useQueryClient();
  const [showScanner, setShowScanner] = useState(false);
  const [scannedToken, setScannedToken] = useState<string | null>(null);
  const [checkoutData, setCheckoutData] = useState<CheckoutResponse | null>(null);

  // Checkout mutation
  const checkoutMutation = useMutation({
    mutationFn: (tokenCode: string) => checkinApi.checkout(tokenCode),
    onSuccess: (response) => {
      setCheckoutData(response);
      notifications.show({
        title: 'Check-out completato!',
        message: `Bici da ${response.checkin.position}`,
        color: 'green',
        icon: <IconCheck />,
      });
      
      // Refresh data
      queryClient.invalidateQueries({ queryKey: ['checkins'] });
      queryClient.invalidateQueries({ queryKey: ['eventStats'] });
      queryClient.invalidateQueries({ queryKey: ['nextSlot'] });
    },
    onError: (error: Error) => {
      notifications.show({
        title: 'Errore',
        message: error.message,
        color: 'red',
      });
    },
  });

  const handleScan = (code: string) => {
    const tokenCode = code.includes('/t/') ? code.split('/t/')[1] : code;
    setScannedToken(tokenCode.toUpperCase());
    setShowScanner(false);
    
    // Immediately try checkout
    checkoutMutation.mutate(tokenCode.toUpperCase());
  };

  const handleReset = () => {
    setScannedToken(null);
    setCheckoutData(null);
  };

  return (
    <Stack gap="lg">
      <Title order={2}>Check-out Bici</Title>

      {!checkoutData ? (
        <Paper withBorder p="lg" radius="md">
          <Stack>
            {showScanner ? (
              <QRScanner onScan={handleScan} onClose={() => setShowScanner(false)} />
            ) : (
              <Button
                size="xl"
                leftSection={<IconQrcode size={24} />}
                onClick={() => setShowScanner(true)}
                loading={checkoutMutation.isPending}
              >
                Scansiona QR Cliente
              </Button>
            )}

            {scannedToken && checkoutMutation.isPending && (
              <Alert color="blue" title="Elaborazione...">
                🎫 {scannedToken}
              </Alert>
            )}

            {checkoutMutation.isError && (
              <Alert color="red" title="Errore">
                {checkoutMutation.error.message}
                <Button mt="sm" variant="light" color="red" onClick={handleReset}>
                  Riprova
                </Button>
              </Alert>
            )}

            <Button
              variant="subtle"
              color="gray"
              onClick={() => {/* TODO: Navigate to search */}}
            >
              ❓ Token smarrito? Cerca bici
            </Button>
          </Stack>
        </Paper>
      ) : (
        <Paper withBorder p="lg" radius="md">
          <Stack>
            <Alert color="green" title="✅ Check-out completato!" variant="filled">
              La bici è stata restituita
            </Alert>

            <Paper p="md" withBorder>
              <Stack gap="sm">
                <Group>
                  <IconMapPin size={20} />
                  <Text fw={600} size="lg">{checkoutData.checkin.position}</Text>
                </Group>
                
                <Group>
                  <IconClock size={20} />
                  <Text>
                    Check-in: {new Date(checkoutData.checkin.checked_in_at).toLocaleString('it-IT')}
                  </Text>
                </Group>

                <Badge color={checkoutData.token_type === 'digital' ? 'blue' : 'orange'}>
                  {checkoutData.token_type === 'digital' ? '📱' : '📵'} Token {checkoutData.token_type}
                </Badge>

                {checkoutData.customer?.phone_masked && (
                  <Text size="sm" c="dimmed">
                    📱 {checkoutData.customer.phone_masked}
                  </Text>
                )}
              </Stack>
            </Paper>

            {checkoutData.checkin.bike_photo_url && (
              <Paper p="md" withBorder>
                <Text fw={500} mb="sm">📸 Foto bici</Text>
                <Image
                  src={checkoutData.checkin.bike_photo_url}
                  alt="Foto bici"
                  radius="md"
                  mah={300}
                  fit="contain"
                />
              </Paper>
            )}

            <Button size="lg" onClick={handleReset}>
              Prossimo check-out
            </Button>
          </Stack>
        </Paper>
      )}
    </Stack>
  );
}

