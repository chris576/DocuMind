import { Injectable, Logger, OnModuleInit, OnModuleDestroy } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as amqplib from 'amqplib';

type AmqpConnection = ReturnType<typeof amqplib.connect> extends Promise<infer T> ? T : never;
type AmqpChannel = Awaited<ReturnType<AmqpConnection['createChannel']>>;

export enum PipelineRoutingKey {
  INGESTION = 'pipeline.ingestion',
  RETRIEVAL = 'pipeline.retrieval',
  GENERATION = 'pipeline.generation',
  STATUS = 'pipeline.status',
}

export interface PipelineMessage {
  action: string;
  [key: string]: any;
}

@Injectable()
export class MessagingService implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(MessagingService.name);
  private connection: AmqpConnection | null = null;
  private channel: AmqpChannel | null = null;
  private exchangeName = 'paperless_ai';
  private connected = false;

  constructor(private configService: ConfigService) {}

  async onModuleInit() {
    await this.connect();
  }

  async onModuleDestroy() {
    await this.close();
  }

  async connect() {
    try {
      const url = this.configService.get<string>('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/');
      this.connection = await amqplib.connect(url);
      this.channel = await this.connection.createChannel();
      await this.channel.assertExchange(this.exchangeName, 'topic', { durable: true });
      this.connected = true;
      this.logger.log('Connected to RabbitMQ');
    } catch (error) {
      this.connected = false;
      const message = error instanceof Error ? error.message : String(error);
      this.logger.warn(`RabbitMQ connection failed: ${message}`);
    }
  }

  async publish(routingKey: PipelineRoutingKey, message: PipelineMessage) {
    if (!this.connected || !this.channel) {
      this.logger.warn(`RabbitMQ not connected, message dropped: ${routingKey}`);
      return false;
    }

    try {
      const buffer = Buffer.from(JSON.stringify(message));
      this.channel.publish(this.exchangeName, routingKey, buffer, {
        contentType: 'application/json',
        persistent: true,
      });
      this.logger.debug(`Published message to ${routingKey}`);
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      this.logger.error(`Failed to publish message: ${message}`);
      return false;
    }
  }

  async close() {
    if (this.channel) {
      await this.channel.close();
    }
    if (this.connection) {
      await this.connection.close();
    }
    this.connected = false;
    this.logger.log('RabbitMQ connection closed');
  }

  isConnected(): boolean {
    return this.connected;
  }
}
