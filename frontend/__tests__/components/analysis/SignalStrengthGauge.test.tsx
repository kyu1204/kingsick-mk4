import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SignalStrengthGauge } from '@/components/analysis/SignalStrengthGauge'

describe('SignalStrengthGauge', () => {
  it('renders correctly with score and signal', () => {
    render(<SignalStrengthGauge strength={85} signal="STRONG_BUY" />)
    
    expect(screen.getByText('85')).toBeInTheDocument()
    expect(screen.getByText('STRONG BUY')).toBeInTheDocument()
    expect(screen.getByText('점수')).toBeInTheDocument()
  })

  it('applies correct colors for BUY signal', () => {
    const { container } = render(<SignalStrengthGauge strength={80} signal="BUY" />)
    
    const scoreElement = screen.getByText('80')
    expect(scoreElement).toHaveClass('text-green-500')
    
    const badge = screen.getByText('BUY').closest('div')
    expect(badge).toHaveClass('border-green-200')
    expect(badge).toHaveClass('text-green-700')
  })

  it('applies correct colors for SELL signal', () => {
    const { container } = render(<SignalStrengthGauge strength={20} signal="SELL" />)
    
    const scoreElement = screen.getByText('20')
    expect(scoreElement).toHaveClass('text-red-500')
    
    const badge = screen.getByText('SELL').closest('div')
    expect(badge).toHaveClass('border-red-200')
    expect(badge).toHaveClass('text-red-700')
  })

  it('applies correct colors for HOLD signal', () => {
    const { container } = render(<SignalStrengthGauge strength={50} signal="HOLD" />)
    
    const scoreElement = screen.getByText('50')
    expect(scoreElement).toHaveClass('text-yellow-500')
    
    const badge = screen.getByText('HOLD').closest('div')
    expect(badge).toHaveClass('border-yellow-200')
    expect(badge).toHaveClass('text-yellow-700')
  })

  it('clamps strength value between 0 and 100', () => {
    render(<SignalStrengthGauge strength={150} signal="STRONG_BUY" />)
    expect(screen.getByText('150')).toBeInTheDocument() 
  })
})
