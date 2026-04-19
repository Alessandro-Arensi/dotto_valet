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
  Badge,
  TextInput,
  Divider,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconQrcode, IconCheck, IconMapPin, IconClock } from '@tabler/icons-react';

import { checkinApi, CheckoutResponse } from '../../api/client';
import { useActiveEventStore } from '../../stores/activeEventStore';
import QRScanner from '../../components/common/QRScanner';

export default function CheckoutPage() {
  const queryClient = useQueryClient();
  const { eventName: activeEventName } = useActiveEventStore();
  const [showScanner, setShowScanner] = useState(false);
  const [scannedToken, setScannedToken] = useState<string | null>(null);
  const [manualCode, setManualCode] = useState('');
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
      <Group justify="space-between" align="flex-end">
        <Title order={2}>Check-out Bici</Title>
        {activeEventName && (
          <Badge size="lg" variant="light" color="blue">
            {activeEventName}
          </Badge>
        )}
      </Group>

      <Text size="sm" c="dimmed">
        Il check-out cerca il token globalmente: funziona anche se il cliente
        è di un evento diverso da quello selezionato.
      </Text>

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

            <Divider label="oppure inserisci codice" labelPosition="center" />

            <Group align="flex-end">
              <TextInput
                flex={1}
                placeholder="DOT-XXXX"
                value={manualCode}
                onChange={(e) => setManualCode(e.currentTarget.value.toUpperCase())}
              />
              <Button
                disabled={!manualCode}
                loading={checkoutMutation.isPending}
                onClick={() => {
                  setScannedToken(manualCode);
                  checkoutMutation.mutate(manualCode);
                }}
              >
                Check-out
              </Button>
            </Group>

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

            {checkoutData.checkin.bike_description && (
              <Paper p="md" withBorder>
                <Text fw={500} mb="sm">📝 Descrizione bici</Text>
                <Text>{checkoutData.checkin.bike_description}</Text>
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


