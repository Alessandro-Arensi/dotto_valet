import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Title,
  Text,
  Paper,
  Group,
  Stack,
  TextInput,
  Button,
  Switch,
  Alert,
  Badge,
  Divider,
  Select,
  Checkbox,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import {
  IconQrcode,
  IconPhone,
  IconMail,
  IconCheck,
  IconAlertCircle,
  IconMapPin,
} from '@tabler/icons-react';

import { eventsApi, checkinApi, CheckinRequest } from '../../api/client';
import QRScanner from '../../components/common/QRScanner';

type Step = 'scan' | 'form' | 'physical';

export default function CheckinPage() {
  const queryClient = useQueryClient();
  const [step, setStep] = useState<Step>('scan');
  const [scannedToken, setScannedToken] = useState<string | null>(null);
  const [isPhysicalToken, setIsPhysicalToken] = useState(false);
  const [autoPosition, setAutoPosition] = useState(true);
  const [showScanner, setShowScanner] = useState(false);

  // Fetch events and next slot
  const { data: events } = useQuery({
    queryKey: ['events'],
    queryFn: () => eventsApi.list(),
  });
  const activeEvent = events?.[0];

  const { data: nextSlot } = useQuery({
    queryKey: ['nextSlot', activeEvent?.id],
    queryFn: () => eventsApi.getNextSlot(activeEvent!.id),
    enabled: !!activeEvent && autoPosition,
  });

  const form = useForm({
    initialValues: {
      phone: '',
      email: '',
      newsletter: false,
    },
  });

  // Checkin mutation
  const checkinMutation = useMutation({
    mutationFn: (data: CheckinRequest) => checkinApi.create(data),
    onSuccess: (response) => {
      notifications.show({
        title: 'Check-in completato!',
        message: `Bici in ${response.position.rack_label || `Rast. ${response.position.rack_number}`}, Slot ${response.position.slot_number}`,
        color: 'green',
        icon: <IconCheck />,
      });
      
      // Reset form
      setStep('scan');
      setScannedToken(null);
      setIsPhysicalToken(false);
      form.reset();
      
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
    // Extract token code from URL if needed
    const tokenCode = code.includes('/t/') ? code.split('/t/')[1] : code;
    setScannedToken(tokenCode.toUpperCase());
    setShowScanner(false);
    setStep('form');
  };

  const handleSubmit = () => {
    const data: CheckinRequest = {
      token_code: scannedToken || `NEW-${Date.now()}`,
      create_token: !scannedToken,
      customer_phone: form.values.phone || undefined,
      customer_email: form.values.email || undefined,
      newsletter_opt_in: form.values.newsletter,
      physical_token: isPhysicalToken,
      auto_position: autoPosition,
      rack_id: autoPosition ? undefined : undefined, // TODO: manual selection
      slot_number: autoPosition ? undefined : undefined,
    };
    
    checkinMutation.mutate(data);
  };

  return (
    <Stack gap="lg">
      <Title order={2}>Check-in Bici</Title>

      {/* Stats badge */}
      {nextSlot && autoPosition && (
        <Alert variant="light" color="blue" icon={<IconMapPin size={16} />}>
          Prossimo slot disponibile: <strong>{nextSlot.rack_label || `Rastrelliera ${nextSlot.rack_number}`}, Slot {nextSlot.slot_number}</strong>
        </Alert>
      )}

      {/* Step: Scan */}
      {step === 'scan' && (
        <Paper withBorder p="lg" radius="md">
          <Stack>
            <Text fw={500} size="lg">🎫 Token Digitale (consigliato)</Text>
            
            {showScanner ? (
              <QRScanner onScan={handleScan} onClose={() => setShowScanner(false)} />
            ) : (
              <Button
                size="lg"
                leftSection={<IconQrcode size={20} />}
                onClick={() => setShowScanner(true)}
              >
                Scansiona QR Cliente
              </Button>
            )}

            <Divider label="oppure nuovo cliente" labelPosition="center" />

            <TextInput
              label="Telefono cliente"
              placeholder="+39 333 1234567"
              leftSection={<IconPhone size={16} />}
              {...form.getInputProps('phone')}
            />
            
            <TextInput
              label="Email (opzionale)"
              placeholder="mario@email.it"
              leftSection={<IconMail size={16} />}
              {...form.getInputProps('email')}
            />
            
            <Checkbox
              label="Iscriviti alla newsletter"
              {...form.getInputProps('newsletter', { type: 'checkbox' })}
            />

            {form.values.phone && (
              <Button onClick={() => setStep('form')}>
                Continua →
              </Button>
            )}

            <Divider />
            
            <Button
              variant="subtle"
              color="gray"
              onClick={() => {
                setIsPhysicalToken(true);
                setStep('physical');
              }}
            >
              📵 Cliente senza smartphone? Usa token fisico
            </Button>
          </Stack>
        </Paper>
      )}

      {/* Step: Form (after scan or phone input) */}
      {step === 'form' && !isPhysicalToken && (
        <Paper withBorder p="lg" radius="md">
          <Stack>
            {scannedToken && (
              <Alert color="green" title="Token riconosciuto">
                🎫 {scannedToken}
              </Alert>
            )}

            {/* Position */}
            <Paper p="md" withBorder>
              <Group justify="space-between" mb="sm">
                <Text fw={500}>📍 Posizione automatica</Text>
                <Switch
                  checked={autoPosition}
                  onChange={(e) => setAutoPosition(e.currentTarget.checked)}
                  size="lg"
                  color="teal"
                />
              </Group>
              
              {autoPosition && nextSlot && (
                <Badge size="lg" color="teal">
                  {nextSlot.rack_label || `Rast. ${nextSlot.rack_number}`}, Slot {nextSlot.slot_number}
                </Badge>
              )}
            </Paper>

            {/* Info for digital token */}
            <Alert color="blue" variant="light">
              💡 Token digitale: nessuna foto necessaria. Il cliente può sempre recuperare il QR tramite il suo numero di telefono.
            </Alert>

            <Group>
              <Button variant="light" onClick={() => setStep('scan')}>
                ← Indietro
              </Button>
              <Button
                flex={1}
                loading={checkinMutation.isPending}
                onClick={handleSubmit}
                leftSection={<IconCheck />}
              >
                Conferma Check-in
              </Button>
            </Group>
          </Stack>
        </Paper>
      )}

      {/* Step: Physical token */}
      {step === 'physical' && (
        <Paper withBorder p="lg" radius="md">
          <Stack>
            <Alert color="yellow" title="Token Fisico">
              Usa solo se il cliente NON ha smartphone disponibile.
            </Alert>

            {showScanner ? (
              <QRScanner onScan={handleScan} onClose={() => setShowScanner(false)} />
            ) : (
              <Button
                size="lg"
                color="orange"
                leftSection={<IconQrcode size={20} />}
                onClick={() => setShowScanner(true)}
              >
                Scansiona Gettone Fisico
              </Button>
            )}

            {scannedToken && (
              <>
                <Alert color="orange" title="Token scansionato">
                  🎫 {scannedToken}
                </Alert>

                {/* Position */}
                <Paper p="md" withBorder>
                  <Group justify="space-between" mb="sm">
                    <Text fw={500}>📍 Posizione automatica</Text>
                    <Switch
                      checked={autoPosition}
                      onChange={(e) => setAutoPosition(e.currentTarget.checked)}
                      size="lg"
                      color="teal"
                    />
                  </Group>
                  
                  {autoPosition && nextSlot && (
                    <Badge size="lg" color="teal">
                      {nextSlot.rack_label || `Rast. ${nextSlot.rack_number}`}, Slot {nextSlot.slot_number}
                    </Badge>
                  )}
                </Paper>

                {/* Photo required for physical */}
                <Paper p="md" withBorder bg="orange.0">
                  <Text fw={600} mb="sm">📸 Foto Bici (OBBLIGATORIA)</Text>
                  <Text size="sm" c="dimmed" mb="md">
                    La foto è necessaria per identificare la bici in caso di smarrimento del gettone.
                  </Text>
                  <Button color="orange">
                    📷 Scatta foto bici
                  </Button>
                </Paper>

                <Alert color="yellow" variant="light">
                  📋 Ricorda: consegna il gettone al cliente dopo il check-in!
                </Alert>

                <Group>
                  <Button variant="light" onClick={() => {
                    setStep('scan');
                    setScannedToken(null);
                    setIsPhysicalToken(false);
                  }}>
                    ← Indietro
                  </Button>
                  <Button
                    flex={1}
                    color="orange"
                    loading={checkinMutation.isPending}
                    onClick={handleSubmit}
                    leftSection={<IconCheck />}
                  >
                    Conferma Check-in
                  </Button>
                </Group>
              </>
            )}

            {!scannedToken && (
              <Button variant="light" onClick={() => {
                setStep('scan');
                setIsPhysicalToken(false);
              }}>
                ← Torna a token digitale
              </Button>
            )}
          </Stack>
        </Paper>
      )}
    </Stack>
  );
}


